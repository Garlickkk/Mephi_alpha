from __future__ import annotations

import hashlib
import math
import os
from datetime import date, datetime, timezone
from typing import Literal, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Alfa Hack Decision & Scoring Service",
    description="Decision-service adapter for application_server + formalized SME scoring engine",
    version="1.0.0",
)

SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "change-me-internal-token")


class ProductDto(BaseModel):
    id: int
    title: str
    interest: float
    discountInterest: Optional[float] = None
    discountConditions: Optional[str] = None
    minSum: Optional[int] = None
    maxSum: Optional[int] = None
    minDurationYear: Optional[int] = None
    maxDurationYear: Optional[int] = None
    repaymentTypes: Optional[list[str]] = None
    mainDifference: Optional[str] = None


class ClientInfo(BaseModel):
    inn: str
    organizationType: Literal["OOO", "IP", "AO"]
    okvedMain: str
    registrationDate: date


class LoanInfo(BaseModel):
    rate: float = Field(gt=0)
    amount: float = Field(gt=0)
    durationYears: int = Field(ge=1, le=30)
    purpose: str
    collateral: bool


class DecisionRequest(BaseModel):
    applicationId: int
    client: ClientInfo
    loan: LoanInfo
    product: Optional[ProductDto] = None
    requestedAt: datetime


class CounterOffer(BaseModel):
    rate: Optional[float] = None
    amount: Optional[float] = None
    durationYears: Optional[int] = None


class DecisionResponse(BaseModel):
    decisionId: str
    outcome: Literal["APPROVED", "REJECTED", "COUNTER_OFFER", "PENDING"]
    comment: str
    counterOffer: Optional[CounterOffer] = None
    score: Optional[int] = None
    riskGrade: Optional[str] = None
    interestRate: Optional[float] = None
    monthlyPayment: Optional[float] = None
    dtiRatio: Optional[float] = None
    profitabilityMargin: Optional[float] = None


class ScoringInput(BaseModel):
    client_id: str
    business_type: Literal["ИП", "ООО"]
    business_age_months: int
    okved_category: Literal["it", "trade", "production", "services", "construction", "horeca"]
    monthly_income: float
    monthly_expenses: float
    current_debts_payment: float
    credit_history: Literal["good", "none", "bad"]
    requested_amount: float
    requested_term_months: int
    has_collateral: bool
    collateral_value: float


class ScoringResult(BaseModel):
    decision: Literal["APPROVED", "COUNTER_OFFER", "REJECTED"]
    reason: str
    score: int
    risk_grade: str
    interest_rate: float
    approved_amount: float
    approved_term_months: int
    monthly_payment: float
    dti_ratio: float
    profitability_margin: float


def calc_annuity_payment(amount: float, annual_rate: float, term_months: int) -> float:
    if amount <= 0 or term_months <= 0:
        return 0.0
    monthly_rate = (annual_rate / 100.0) / 12.0
    if monthly_rate == 0:
        return amount / term_months
    factor = (monthly_rate * math.pow(1 + monthly_rate, term_months)) / (
        math.pow(1 + monthly_rate, term_months) - 1
    )
    return amount * factor


def calc_max_amount_from_payment(max_payment: float, annual_rate: float, term_months: int) -> float:
    if max_payment <= 0 or term_months <= 0:
        return 0.0
    monthly_rate = (annual_rate / 100.0) / 12.0
    if monthly_rate == 0:
        return max_payment * term_months
    factor = (monthly_rate * math.pow(1 + monthly_rate, term_months)) / (
        math.pow(1 + monthly_rate, term_months) - 1
    )
    return max_payment / factor


def evaluate_scoring(req: ScoringInput) -> ScoringResult:
    net_profit = req.monthly_income - req.monthly_expenses
    margin = (net_profit / req.monthly_income * 100.0) if req.monthly_income > 0 else 0.0
    free_cash_flow = net_profit - req.current_debts_payment

    if net_profit <= 0 or free_cash_flow <= 10000:
        return ScoringResult(decision="REJECTED", reason="Убыточная деятельность или свободный денежный поток после уплаты текущих долгов менее 10 000 руб/мес.", score=0, risk_grade="E", interest_rate=0.0, approved_amount=0.0, approved_term_months=0, monthly_payment=0.0, dti_ratio=1.0, profitability_margin=round(margin, 2))

    if req.credit_history == "bad" and not req.has_collateral:
        return ScoringResult(decision="REJECTED", reason="Наличие открытых просрочек в БКИ при отсутствии залогового обеспечения.", score=10, risk_grade="E", interest_rate=0.0, approved_amount=0.0, approved_term_months=0, monthly_payment=0.0, dti_ratio=1.0, profitability_margin=round(margin, 2))

    is_young_business = (req.business_type == "ООО" and req.business_age_months < 9) or (req.business_type == "ИП" and req.business_age_months < 3)
    if is_young_business and req.credit_history == "bad":
        return ScoringResult(decision="REJECTED", reason="Для нового бизнеса критично отсутствие негативной кредитной истории.", score=15, risk_grade="E", interest_rate=0.0, approved_amount=0.0, approved_term_months=0, monthly_payment=0.0, dti_ratio=1.0, profitability_margin=round(margin, 2))

    score = 30
    if is_young_business:
        score -= 10
    elif req.business_age_months < 12:
        score += 5
    elif req.business_age_months <= 36:
        score += 15
    else:
        score += 25

    score += {"good": 25, "none": 5, "bad": -30}.get(req.credit_history, 0)

    if req.has_collateral and req.collateral_value > 0:
        collateral_coverage = req.collateral_value / req.requested_amount
        if collateral_coverage >= 1.2:
            score += 25
        elif collateral_coverage >= 0.7:
            score += 15
        else:
            score += 5

    score += {"it": 15, "production": 15, "trade": 10, "services": 10, "horeca": -5, "construction": -10}.get(req.okved_category, 0)

    if margin >= 25:
        score += 15
    elif margin >= 10:
        score += 10
    elif margin < 5:
        score -= 10

    if score >= 85:
        grade, base_rate, max_dti_limit = "A", 16.5, 0.60
    elif score >= 65:
        grade, base_rate, max_dti_limit = "B", 18.5, 0.50
    elif score >= 45:
        grade, base_rate, max_dti_limit = "C", 21.0, 0.40
    elif score >= 30:
        grade, base_rate, max_dti_limit = "D", 24.5, 0.30
    else:
        return ScoringResult(decision="REJECTED", reason=f"Недостаточный скоринговый балл ({score} из минимальных 30). Высокий совокупный риск.", score=score, risk_grade="E", interest_rate=0.0, approved_amount=0.0, approved_term_months=0, monthly_payment=0.0, dti_ratio=1.0, profitability_margin=round(margin, 2))

    if req.has_collateral and req.collateral_value >= req.requested_amount:
        base_rate -= 1.5

    req_monthly_payment = calc_annuity_payment(req.requested_amount, base_rate, req.requested_term_months)
    projected_dti = (req.current_debts_payment + req_monthly_payment) / net_profit
    young_business_cap = 500_000.0 if not req.has_collateral else min(1_500_000.0, req.collateral_value * 0.8)

    if projected_dti <= max_dti_limit and (not is_young_business or req.requested_amount <= young_business_cap):
        return ScoringResult(decision="APPROVED", reason="Заявка полностью соответствует критериям финансовой устойчивости.", score=score, risk_grade=grade, interest_rate=round(base_rate, 2), approved_amount=round(req.requested_amount, 2), approved_term_months=req.requested_term_months, monthly_payment=round(req_monthly_payment, 2), dti_ratio=round(projected_dti, 2), profitability_margin=round(margin, 2))

    max_affordable_new_payment = (net_profit * max_dti_limit) - req.current_debts_payment
    if max_affordable_new_payment <= 5000:
        return ScoringResult(decision="REJECTED", reason="Высокая текущая закредитованность не позволяет выделить лимит под новый платеж.", score=score, risk_grade=grade, interest_rate=0.0, approved_amount=0.0, approved_term_months=0, monthly_payment=0.0, dti_ratio=round(projected_dti, 2), profitability_margin=round(margin, 2))

    max_allowed_term = 18 if is_young_business else 60
    best_term = req.requested_term_months
    if req.requested_term_months <= max_allowed_term:
        for term in range(req.requested_term_months, max_allowed_term + 1, 6):
            if calc_annuity_payment(req.requested_amount, base_rate, term) <= max_affordable_new_payment:
                best_term = term
                break

    recalculated_payment = calc_annuity_payment(req.requested_amount, base_rate, best_term)
    if recalculated_payment <= max_affordable_new_payment and (not is_young_business or req.requested_amount <= young_business_cap):
        new_dti = (req.current_debts_payment + recalculated_payment) / net_profit
        return ScoringResult(decision="COUNTER_OFFER", reason=f"Для комфортной долговой нагрузки предлагаем увеличить срок кредита с {req.requested_term_months} до {best_term} мес.", score=score, risk_grade=grade, interest_rate=round(base_rate, 2), approved_amount=round(req.requested_amount, 2), approved_term_months=best_term, monthly_payment=round(recalculated_payment, 2), dti_ratio=round(new_dti, 2), profitability_margin=round(margin, 2))

    safe_amount = calc_max_amount_from_payment(max_affordable_new_payment, base_rate, max_allowed_term)
    if is_young_business:
        safe_amount = min(safe_amount, young_business_cap)
        reason_text = "Стартовый предел финансирования для нового бизнеса (ИП < 3 мес / ООО < 9 мес) на основе текущей прибыли."
    else:
        reason_text = "Запрошенная сумма превышает лимит долговой нагрузки. Предлагаем сниженную безопасную сумму."

    safe_amount = math.floor(safe_amount / 10000.0) * 10000.0
    if safe_amount < 50_000:
        return ScoringResult(decision="REJECTED", reason="Рассчитанный безопасный лимит кредитования составляет менее минимальных 50 000 руб.", score=score, risk_grade=grade, interest_rate=0.0, approved_amount=0.0, approved_term_months=0, monthly_payment=0.0, dti_ratio=round(projected_dti, 2), profitability_margin=round(margin, 2))

    final_payment = calc_annuity_payment(safe_amount, base_rate, max_allowed_term)
    final_dti = (req.current_debts_payment + final_payment) / net_profit
    return ScoringResult(decision="COUNTER_OFFER", reason=reason_text, score=score, risk_grade=grade, interest_rate=round(base_rate, 2), approved_amount=round(safe_amount, 2), approved_term_months=max_allowed_term, monthly_payment=round(final_payment, 2), dti_ratio=round(final_dti, 2), profitability_margin=round(margin, 2))


def months_since(registration_date: date) -> int:
    today = date.today()
    months = (today.year - registration_date.year) * 12 + today.month - registration_date.month
    if today.day < registration_date.day:
        months -= 1
    return max(months, 0)


def map_okved_category(okved: str) -> str:
    try:
        section = int(okved.strip().split(".")[0])
    except (ValueError, AttributeError):
        return "services"
    if 62 <= section <= 63:
        return "it"
    if 45 <= section <= 47:
        return "trade"
    if 10 <= section <= 33:
        return "production"
    if 41 <= section <= 43:
        return "construction"
    if 55 <= section <= 56:
        return "horeca"
    return "services"


def deterministic_external_mocks(request: DecisionRequest) -> tuple[float, float, float, str, float]:
    """Local stand-ins for bank turnover/BKI/collateral valuation.

    Stable per INN so the same demo client gets the same enrichment every run.
    Replace this function with real adapters when those sources are available.
    """
    digest = hashlib.sha256(request.client.inn.encode("utf-8")).digest()
    income = 1_500_000.0 + (int.from_bytes(digest[0:2], "big") % 4_500_001)
    expense_ratio = 0.55 + (digest[2] / 255.0) * 0.25
    expenses = income * expense_ratio
    debt_payment = (digest[3] / 255.0) * income * 0.08
    history_bucket = digest[4] % 10
    credit_history = "good" if history_bucket < 7 else ("none" if history_bucket < 9 else "bad")
    collateral_value = request.loan.amount * (1.2 if request.loan.collateral else 0.0)
    return income, expenses, debt_payment, credit_history, collateral_value


def to_scoring_input(request: DecisionRequest) -> ScoringInput:
    income, expenses, debts, history, collateral_value = deterministic_external_mocks(request)
    # The current backend enum has AO, while the supplied scoring card only distinguishes ИП/ООО.
    # For the MVP, AO follows the ООО thresholds rather than failing the whole request.
    business_type = "ИП" if request.client.organizationType == "IP" else "ООО"
    return ScoringInput(
        client_id=request.client.inn,
        business_type=business_type,
        business_age_months=months_since(request.client.registrationDate),
        okved_category=map_okved_category(request.client.okvedMain),
        monthly_income=income,
        monthly_expenses=expenses,
        current_debts_payment=debts,
        credit_history=history,
        requested_amount=request.loan.amount,
        requested_term_months=request.loan.durationYears * 12,
        has_collateral=request.loan.collateral,
        collateral_value=collateral_value,
    )


@app.post("/api/v1/decisions", response_model=DecisionResponse)
def decide(
    request: DecisionRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    service_token: Optional[str] = Header(None, alias="X-Service-Token"),
):
    if service_token != SERVICE_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid X-Service-Token")
    if idempotency_key != str(request.applicationId):
        raise HTTPException(status_code=409, detail="Idempotency-Key must equal applicationId")

    result = evaluate_scoring(to_scoring_input(request))
    decision_id = f"score-{request.applicationId}"
    counter_offer = None
    if result.decision == "COUNTER_OFFER":
        counter_offer = CounterOffer(
            rate=result.interest_rate,
            amount=result.approved_amount,
            durationYears=max(1, math.ceil(result.approved_term_months / 12)),
        )

    return DecisionResponse(
        decisionId=decision_id,
        outcome=result.decision,
        comment=result.reason,
        counterOffer=counter_offer,
        score=result.score,
        riskGrade=result.risk_grade,
        interestRate=result.interest_rate,
        monthlyPayment=result.monthly_payment,
        dtiRatio=result.dti_ratio,
        profitabilityMargin=result.profitability_margin,
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "decision-scoring"}
