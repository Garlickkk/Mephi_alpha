from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from typing import Literal, Optional

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, Request, Response, Security
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(
    title="Alfa Hack Decision & Scoring Service",
    description="Decision-service adapter for application_server + formalized SME scoring engine",
    version="1.1.0",
)
log = logging.getLogger("decision_service")

SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "change-me-internal-token")
APPLICATION_SERVICE_URL = os.getenv("APPLICATION_SERVICE_URL", "http://localhost:8083")

# Кредитная политика встречного предложения
MAX_EXTENSION_YEARS = 5  # до какого срока банк сам растягивает кредит
YOUNG_MAX_TERM_YEARS = 1  # ИП < 3 мес / ООО < 9 мес; было 18 мес., округлено вниз до целого года
MIN_LOAN_AMOUNT = 50_000.0

# Ручная проверка: модель решает понятные случаи, пограничные отдаёт сотруднику
MANUAL_REVIEW_GRADES = {"D"}
MANUAL_REVIEW_AMOUNT = 30_000_000.0

# Повторы callback'а (раздел 5 контракта): паузы между 5 попытками
CALLBACK_RETRY_DELAYS = (1, 2, 4, 8)


def error_body(message: str) -> dict:
    """Формат ошибок, общий для всех сервисов бекенда: {message, dateTime}."""
    return {"message": message, "dateTime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")}


@app.middleware("http")
async def require_service_token(request: Request, call_next):
    # Проверка до разбора тела: запрос без токена получает 403, а не ошибку валидации
    if request.url.path.startswith("/api/v1/") and request.headers.get("X-Service-Token") != SERVICE_TOKEN:
        return JSONResponse(status_code=403, content=error_body("Неверный или отсутствующий X-Service-Token"))
    return await call_next(request)


# Заголовок для Swagger (кнопка Authorize); сама проверка — в middleware выше
service_token_header = APIKeyHeader(name="X-Service-Token", auto_error=False)


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=error_body(str(exc.detail)))


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Контракт обещает 400 на некорректные данные (FastAPI по умолчанию отвечает 422)
    details = "; ".join(f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors())
    return JSONResponse(status_code=400, content=error_body(f"Некорректные данные: {details}"))


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
    # Заявка хранит срок в целых годах, поэтому и встречное предложение считается в годах
    requested_term_years: int
    # Ставка заявки (из продукта или калькулятора): по ней считаются платёж и DTI
    annual_rate: float
    has_collateral: bool
    collateral_value: float
    # Лимиты выбранного продукта; None, если заявка подана через калькулятор без продукта
    product_min_sum: Optional[float] = None
    product_max_sum: Optional[float] = None
    product_max_term_years: Optional[int] = None


class ScoringResult(BaseModel):
    """Метрики, которые для данного исхода не имеют смысла (ставка и платёж при отказе), равны None."""
    decision: Literal["APPROVED", "COUNTER_OFFER", "REJECTED"]
    reason: str
    score: Optional[int] = None
    risk_grade: Optional[str] = None
    interest_rate: Optional[float] = None
    approved_amount: Optional[float] = None
    approved_term_months: Optional[int] = None
    monthly_payment: Optional[float] = None
    dti_ratio: Optional[float] = None
    profitability_margin: Optional[float] = None


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
    margin = round((net_profit / req.monthly_income * 100.0) if req.monthly_income > 0 else 0.0, 2)
    free_cash_flow = net_profit - req.current_debts_payment

    def reject(reason: str, score: Optional[int] = None, grade: Optional[str] = None,
               dti: Optional[float] = None) -> ScoringResult:
        return ScoringResult(decision="REJECTED", reason=reason, score=score, risk_grade=grade,
                             dti_ratio=dti, profitability_margin=margin)

    # Стоп-факторы: скоринговый балл не считается
    if net_profit <= 0 or free_cash_flow <= 0:
        return reject("Убыточная деятельность или платежи по текущим кредитам превышают прибыль.")

    # Плохую историю компенсирует только залог, полностью покрывающий кредит
    collateral_covers_loan = req.has_collateral and req.collateral_value >= req.requested_amount
    if req.credit_history == "bad" and not collateral_covers_loan:
        return reject("Наличие открытых просрочек в БКИ при отсутствии залога, покрывающего сумму кредита.")

    is_young_business = (req.business_type == "ООО" and req.business_age_months < 9) or (req.business_type == "ИП" and req.business_age_months < 3)
    if is_young_business and req.credit_history == "bad":
        return reject("Для нового бизнеса критично отсутствие негативной кредитной истории.")

    # Балльная карта. Залог в баллы не входит: он снижает потери банка при дефолте (LGD),
    # а не вероятность дефолта, и учитывается в лимитах и стоп-факторах.
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
    score += {"it": 15, "production": 15, "trade": 10, "services": 10, "horeca": -5, "construction": -10}.get(req.okved_category, 0)

    if margin >= 25:
        score += 15
    elif margin >= 10:
        score += 10
    elif margin < 5:
        score -= 10

    # Рейтинг задаёт только допустимую долговую нагрузку. Ставку определяет продукт (или калькулятор),
    # иначе одобрение «под 12,5%» считалось бы по платежу под 18,5% и клиент видел бы не те условия.
    if score >= 85:
        grade, max_dti_limit = "A", 0.60
    elif score >= 65:
        grade, max_dti_limit = "B", 0.50
    elif score >= 45:
        grade, max_dti_limit = "C", 0.40
    elif score >= 30:
        grade, max_dti_limit = "D", 0.30
    else:
        return reject(f"Недостаточный скоринговый балл ({score} из минимальных 30). Высокий совокупный риск.", score=score, grade="E")

    rate = req.annual_rate
    req_years = req.requested_term_years
    req_monthly_payment = calc_annuity_payment(req.requested_amount, rate, req_years * 12)
    projected_dti = (req.current_debts_payment + req_monthly_payment) / net_profit
    young_business_cap = 500_000.0 if not req.has_collateral else min(1_500_000.0, req.collateral_value * 0.8)
    amount_within_young_cap = not is_young_business or req.requested_amount <= young_business_cap

    if projected_dti <= max_dti_limit and amount_within_young_cap:
        return ScoringResult(decision="APPROVED", reason="Заявка полностью соответствует критериям финансовой устойчивости.", score=score, risk_grade=grade, interest_rate=round(rate, 2), approved_amount=round(req.requested_amount, 2), approved_term_months=req_years * 12, monthly_payment=round(req_monthly_payment, 2), dti_ratio=round(projected_dti, 2), profitability_margin=margin)

    max_affordable_new_payment = (net_profit * max_dti_limit) - req.current_debts_payment
    if max_affordable_new_payment <= 0:
        return reject("Высокая текущая закредитованность не позволяет выделить лимит под новый платеж.", score=score, grade=grade, dti=round(projected_dti, 2))

    # Максимальный срок встречного предложения. Молодому бизнесу срок ограничен политикой,
    # остальным срок можно растянуть до MAX_EXTENSION_YEARS, но не короче запрошенного.
    # В любом случае не дольше, чем разрешает продукт.
    if is_young_business:
        max_term_years = YOUNG_MAX_TERM_YEARS
    else:
        max_term_years = max(req_years, MAX_EXTENSION_YEARS)
    if req.product_max_term_years is not None:
        max_term_years = min(max_term_years, req.product_max_term_years)
    max_term_years = max(max_term_years, 1)

    # Попытка А: та же сумма, срок длиннее (целыми годами, как хранит заявка)
    if amount_within_young_cap:
        for years in range(req_years + 1, max_term_years + 1):
            payment = calc_annuity_payment(req.requested_amount, rate, years * 12)
            if payment <= max_affordable_new_payment:
                new_dti = (req.current_debts_payment + payment) / net_profit
                return ScoringResult(decision="COUNTER_OFFER", reason=f"Для комфортной долговой нагрузки предлагаем увеличить срок кредита с {req_years} до {years} лет.", score=score, risk_grade=grade, interest_rate=round(rate, 2), approved_amount=round(req.requested_amount, 2), approved_term_months=years * 12, monthly_payment=round(payment, 2), dti_ratio=round(new_dti, 2), profitability_margin=margin)

    # Попытка Б: сумма меньше, срок максимальный из допустимых
    safe_amount = calc_max_amount_from_payment(max_affordable_new_payment, rate, max_term_years * 12)
    if is_young_business:
        safe_amount = min(safe_amount, young_business_cap)
        reason_text = f"Стартовый предел финансирования для нового бизнеса (ИП < 3 мес / ООО < 9 мес): срок до {max_term_years} г., сумма по текущей прибыли."
    else:
        reason_text = "Запрошенная сумма превышает лимит долговой нагрузки. Предлагаем сниженную безопасную сумму."
    if req.product_max_sum is not None:
        safe_amount = min(safe_amount, req.product_max_sum)

    safe_amount = math.floor(safe_amount / 10000.0) * 10000.0
    min_amount = max(MIN_LOAN_AMOUNT, req.product_min_sum or 0.0)
    if safe_amount < min_amount:
        return reject(f"Рассчитанный безопасный лимит кредитования меньше минимальной суммы {min_amount:,.0f} руб.".replace(",", " "), score=score, grade=grade, dti=round(projected_dti, 2))

    final_payment = calc_annuity_payment(safe_amount, rate, max_term_years * 12)
    final_dti = (req.current_debts_payment + final_payment) / net_profit
    return ScoringResult(decision="COUNTER_OFFER", reason=reason_text, score=score, risk_grade=grade, interest_rate=round(rate, 2), approved_amount=round(safe_amount, 2), approved_term_months=max_term_years * 12, monthly_payment=round(final_payment, 2), dti_ratio=round(final_dti, 2), profitability_margin=margin)


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


# Тестовые клиенты для демонстрации: при регистрации с этим ИНН моки отдают фиксированный профиль.
# ИНН: (выручка/мес, расходы/мес, платежи по кредитам/мес, кредитная история, стоимость залога)
# Ожидаемые исходы и рекомендуемые заявки описаны в README.
DEMO_CLIENTS: dict[str, tuple[float, float, float, str, float]] = {
    "7700000001": (4_000_000.0, 3_200_000.0, 100_000.0, "good", 5_000_000.0),
    "7700000002": (1_000_000.0, 800_000.0, 30_000.0, "good", 0.0),
    "7700000003": (600_000.0, 510_000.0, 20_000.0, "good", 0.0),
    "7700000004": (2_500_000.0, 2_000_000.0, 50_000.0, "bad", 0.0),
    "7700000005": (5_000_000.0, 4_650_000.0, 20_000.0, "bad", 10_000_000.0),
}


def deterministic_external_mocks(request: DecisionRequest) -> tuple[float, float, float, str, float]:
    """Local stand-ins for bank turnover/BKI/collateral valuation.

    Stable per INN so the same demo client gets the same enrichment every run.
    Replace this function with real adapters when those sources are available.
    """
    inn = request.client.inn
    if inn in DEMO_CLIENTS:
        income, expenses, debt_payment, credit_history, collateral = DEMO_CLIENTS[inn]
        return income, expenses, debt_payment, credit_history, collateral if request.loan.collateral else 0.0

    digest = hashlib.sha256(inn.encode("utf-8")).digest()

    def uniform(i: int) -> float:
        return int.from_bytes(digest[i:i + 2], "big") / 65535.0

    # Выручка 0,5–10 млн руб./мес, логравномерно: малого бизнеса больше, чем крупного
    income = 500_000.0 * 20.0 ** uniform(0)
    # Маржа по чистой прибыли от −2% до 28%: около 7% компаний убыточны
    expenses = income * (0.72 + 0.30 * uniform(2))
    # Платежи по текущим кредитам: 0–40% прибыли (у убыточных — до 5% выручки)
    net_profit = income - expenses
    debt_payment = (net_profit * 0.40 if net_profit > 0 else income * 0.05) * uniform(4)
    bucket = digest[6] % 100
    credit_history = "good" if bucket < 65 else ("none" if bucket < 87 else "bad")
    # Оценка залога 1–30 млн руб. не зависит от суммы кредита: галочка «есть залог» не гарантирует покрытие
    collateral_value = 1_000_000.0 * 30.0 ** uniform(7) if request.loan.collateral else 0.0
    return income, expenses, debt_payment, credit_history, collateral_value


def to_scoring_input(request: DecisionRequest) -> ScoringInput:
    income, expenses, debts, history, collateral_value = deterministic_external_mocks(request)
    product = request.product
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
        requested_term_years=request.loan.durationYears,
        annual_rate=request.loan.rate,
        has_collateral=request.loan.collateral,
        collateral_value=collateral_value,
        product_min_sum=product.minSum if product else None,
        product_max_sum=product.maxSum if product else None,
        product_max_term_years=product.maxDurationYear if product else None,
    )


def check_product_limits(request: DecisionRequest) -> None:
    """Повторная проверка лимитов продукта (раздел 7 контракта): нарушение даёт 400."""
    product = request.product
    if product is None:
        return
    amount, years = request.loan.amount, request.loan.durationYears
    if (product.minSum is not None and amount < product.minSum) or (product.maxSum is not None and amount > product.maxSum):
        raise HTTPException(status_code=400, detail=f"Сумма {amount} вне лимитов продукта {product.minSum}–{product.maxSum}")
    if (product.minDurationYear is not None and years < product.minDurationYear) or (product.maxDurationYear is not None and years > product.maxDurationYear):
        raise HTTPException(status_code=400, detail=f"Срок {years} лет вне лимитов продукта {product.minDurationYear}–{product.maxDurationYear}")


def to_decision_response(decision_id: str, request: DecisionRequest, result: ScoringResult) -> DecisionResponse:
    counter_offer = None
    if result.decision == "COUNTER_OFFER":
        # По контракту null означает «без изменений»; ставка задаётся продуктом и не меняется
        years = result.approved_term_months // 12
        counter_offer = CounterOffer(
            rate=None,
            amount=result.approved_amount if result.approved_amount != round(request.loan.amount, 2) else None,
            durationYears=years if years != request.loan.durationYears else None,
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


def manual_review_reason(result: ScoringResult) -> Optional[str]:
    """Пограничные случаи, которые решает сотрудник, а не модель. Отказы по стоп-факторам не пересматриваются."""
    if result.decision == "REJECTED":
        return None
    if result.risk_grade in MANUAL_REVIEW_GRADES:
        return f"Рейтинг {result.risk_grade}: пограничный риск"
    if (result.approved_amount or 0.0) > MANUAL_REVIEW_AMOUNT:
        return f"Сумма выше лимита автоматического решения ({MANUAL_REVIEW_AMOUNT:,.0f} руб.)".replace(",", " ")
    return None


# ---------------------------------------------------------------------------
# Хранилище решений: идемпотентность и ручная проверка.
# В памяти процесса: для прототипа достаточно, при перезапуске история теряется.
# ---------------------------------------------------------------------------
class StoredDecision(BaseModel):
    decisionId: str
    applicationId: int
    fingerprint: str
    status: Literal["DECIDED", "PENDING", "RESOLVED"]
    response: DecisionResponse
    # Что предлагает модель по заявке на ручной проверке; сотрудник может согласиться или решить иначе
    recommendation: Optional[DecisionResponse] = None
    manualReviewReason: Optional[str] = None
    resolvedBy: Optional[str] = None
    callbackStatus: Optional[Literal["IN_PROGRESS", "DELIVERED", "FAILED"]] = None
    createdAt: datetime
    updatedAt: datetime


_decisions: dict[str, StoredDecision] = {}
_decision_by_application: dict[int, str] = {}
_lock = threading.Lock()


def request_fingerprint(request: DecisionRequest) -> str:
    # requestedAt не входит: повторная отправка той же заявки не меняет её содержимое
    payload = request.model_dump(mode="json", exclude={"requestedAt"})
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def http_status_for(stored: StoredDecision) -> int:
    return 202 if stored.response.outcome == "PENDING" else 200


@app.post("/api/v1/decisions", response_model=DecisionResponse, responses={202: {"model": DecisionResponse}},
          dependencies=[Security(service_token_header)])
def decide(
    request: DecisionRequest,
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    if idempotency_key != str(request.applicationId):
        raise HTTPException(status_code=409, detail="Idempotency-Key must equal applicationId")

    fingerprint = request_fingerprint(request)
    with _lock:
        existing_id = _decision_by_application.get(request.applicationId)
        if existing_id is not None:
            existing = _decisions[existing_id]
            if existing.fingerprint != fingerprint:
                raise HTTPException(status_code=409, detail="Idempotency-Key уже использован с другим содержимым заявки")
            response.status_code = http_status_for(existing)
            return existing.response

    check_product_limits(request)
    result = evaluate_scoring(to_scoring_input(request))
    decision_id = f"score-{request.applicationId}"
    model_response = to_decision_response(decision_id, request, result)
    now = datetime.now(timezone.utc)

    review_reason = manual_review_reason(result)
    if review_reason is None:
        stored = StoredDecision(decisionId=decision_id, applicationId=request.applicationId, fingerprint=fingerprint,
                                status="DECIDED", response=model_response, createdAt=now, updatedAt=now)
    else:
        # Клиенту уходит PENDING, метрики скоринга сохраняются, рекомендация модели ждёт сотрудника
        pending = model_response.model_copy(update={
            "outcome": "PENDING", "comment": "Заявка передана сотруднику банка на проверку", "counterOffer": None})
        stored = StoredDecision(decisionId=decision_id, applicationId=request.applicationId, fingerprint=fingerprint,
                                status="PENDING", response=pending, recommendation=model_response,
                                manualReviewReason=review_reason, createdAt=now, updatedAt=now)

    with _lock:
        # Параллельный запрос с тем же ключом мог успеть раньше: побеждает первое решение
        existing_id = _decision_by_application.get(request.applicationId)
        if existing_id is not None:
            stored = _decisions[existing_id]
        else:
            _decisions[decision_id] = stored
            _decision_by_application[request.applicationId] = decision_id

    response.status_code = http_status_for(stored)
    return stored.response


@app.get("/api/v1/decisions/{decision_id}", response_model=StoredDecision, dependencies=[Security(service_token_header)])
def get_decision(decision_id: str):
    stored = _decisions.get(decision_id)
    if stored is None:
        raise HTTPException(status_code=404, detail=f"Решение {decision_id} не найдено")
    return stored


@app.get("/api/v1/decisions", response_model=list[StoredDecision], dependencies=[Security(service_token_header)])
def list_decisions(
    status: Optional[Literal["DECIDED", "PENDING", "RESOLVED"]] = Query(None, description="PENDING — очередь ручной проверки"),
):
    items = [d for d in _decisions.values() if status is None or d.status == status]
    return sorted(items, key=lambda d: d.createdAt)


class ResolveRequest(BaseModel):
    outcome: Literal["APPROVED", "REJECTED", "COUNTER_OFFER"]
    comment: Optional[str] = None
    # Для COUNTER_OFFER: если не передано, берутся условия из рекомендации модели
    counterOffer: Optional[CounterOffer] = None
    reviewer: str = Field("underwriter", description="Кто принял решение, для истории")


@app.post("/api/v1/decisions/{decision_id}/resolve", response_model=StoredDecision, dependencies=[Security(service_token_header)])
def resolve_decision(decision_id: str, body: ResolveRequest, background_tasks: BackgroundTasks):
    """Решение сотрудника по заявке на ручной проверке. Итог уходит в application_server callback'ом."""
    with _lock:
        stored = _decisions.get(decision_id)
        if stored is None:
            raise HTTPException(status_code=404, detail=f"Решение {decision_id} не найдено")
        if stored.status != "PENDING":
            raise HTTPException(status_code=409, detail=f"Решение {decision_id} уже принято (статус {stored.status})")

        counter_offer = None
        if body.outcome == "COUNTER_OFFER":
            counter_offer = body.counterOffer
            if counter_offer is None and stored.recommendation is not None:
                counter_offer = stored.recommendation.counterOffer
            if counter_offer is None or (counter_offer.rate is None and counter_offer.amount is None and counter_offer.durationYears is None):
                raise HTTPException(status_code=400, detail="Для COUNTER_OFFER нужны условия: counterOffer не передан и нет рекомендации модели")

        default_comment = stored.recommendation.comment if stored.recommendation and stored.recommendation.outcome == body.outcome else None
        final = stored.response.model_copy(update={
            "outcome": body.outcome,
            "comment": body.comment or default_comment or "Решение принято сотрудником банка",
            "counterOffer": counter_offer,
        })
        stored.response = final
        stored.status = "RESOLVED"
        stored.resolvedBy = body.reviewer
        stored.callbackStatus = "IN_PROGRESS"
        stored.updatedAt = datetime.now(timezone.utc)

    background_tasks.add_task(send_callback, decision_id)
    return stored


def send_callback(decision_id: str) -> None:
    """POST итогового решения в application_server с повторами при сетевых ошибках и 5xx (раздел 5 контракта)."""
    stored = _decisions[decision_id]
    final = stored.response
    payload = {
        "decisionId": final.decisionId,
        "outcome": final.outcome,
        "comment": final.comment,
        "counterOffer": final.counterOffer.model_dump() if final.counterOffer else None,
    }
    url = f"{APPLICATION_SERVICE_URL}/api/v0/internal/applications/{stored.applicationId}/decision"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    status: Literal["DELIVERED", "FAILED"] = "FAILED"
    for attempt in range(len(CALLBACK_RETRY_DELAYS) + 1):
        req = urllib.request.Request(url, data=data, method="POST", headers={
            "Content-Type": "application/json", "X-Service-Token": SERVICE_TOKEN})
        try:
            with urllib.request.urlopen(req, timeout=5):
                status = "DELIVERED"
                break
        except urllib.error.HTTPError as e:
            if e.code == 409:  # заявка уже в итоговом статусе: попытка считается завершённой
                status = "DELIVERED"
                break
            if e.code < 500:
                log.error("Callback %s отклонён application_server: %s", decision_id, e.code)
                break
            log.warning("Callback %s: %s, попытка %d", decision_id, e.code, attempt + 1)
        except (urllib.error.URLError, OSError) as e:
            log.warning("Callback %s: %s, попытка %d", decision_id, e, attempt + 1)
        if attempt < len(CALLBACK_RETRY_DELAYS):
            time.sleep(CALLBACK_RETRY_DELAYS[attempt])

    with _lock:
        stored.callbackStatus = status
        stored.updatedAt = datetime.now(timezone.utc)


@app.get("/health")
def health():
    return {"status": "ok", "service": "decision-scoring"}
