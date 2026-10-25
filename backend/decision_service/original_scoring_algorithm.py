"""
МИКРОСЕРВИС КРЕДИТНОГО СКОРИНГА МСП (АЛЬФА-ХАК)
Стек: Python 3.11+, FastAPI, Pydantic, Pandas, NumPy.
Назначение: Принимает JSON с анкетными и финансовыми данными ИП/ООО от Kotlin-бэкенда,
рассчитывает скоринговый балл, риск-грейд, персональную ставку, аннуитетный платеж, 
долговую нагрузку (DTI) и возвращает решение (APPROVED, COUNTER_OFFER, REJECTED).

Запуск локально: uvicorn scoring_service:app --host 0.0.0.0 --port 8000 --reload
Swagger UI (документация API): http://localhost:8000/docs
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
import math

app = FastAPI(
    title="Alfa Hack Credit Scoring Engine",
    description="Математическое ядро принятия кредитных решений для малого и микробизнеса",
    version="1.0.0"
)

# =====================================================================
# 1. ВХОДНОЙ КОНТРАКТ ДАННЫХ (От Kotlin-бэкенда в Python) — 12 полей
# =====================================================================
class ScoringRequest(BaseModel):
    # Данные из профиля компании (БД / ЕГРЮЛ / ФНС)
    client_id: str = Field(..., description="Уникальный ID клиента или ИНН", examples=["inn_7701987654"])
    business_type: str = Field(..., description="Форма бизнеса: строго 'ИП' или 'ООО'", examples=["ООО"])
    business_age_months: int = Field(..., ge=0, description="Возраст бизнеса в месяцах", examples=[18])
    okved_category: str = Field(
        ..., 
        description="Отрасль бизнеса: 'it', 'trade', 'production', 'services', 'construction', 'horeca'",
        examples=["trade"]
    )
    
    # Финансовые данные из внутренних систем банка (обороты по РКО)
    monthly_income: float = Field(..., ge=0, description="Среднемесячная выручка / доходы (руб)", examples=[2500000.0])
    monthly_expenses: float = Field(..., ge=0, description="Среднемесячные расходы (руб)", examples=[1900000.0])
    
    # Данные из внешних заглушек (Мок БКИ)
    current_debts_payment: float = Field(..., ge=0, description="Ежемесячный платеж по текущим кредитам (руб)", examples=[100000.0])
    credit_history: str = Field(..., description="Кредитная история из БКИ: 'good', 'none', 'bad'", examples=["good"])
    
    # Данные из кредитного калькулятора (Ввод пользователя на Фронтенде)
    requested_amount: float = Field(..., gt=0, description="Запрашиваемая сумма кредита (руб)", examples=[3000000.0])
    requested_term_months: int = Field(..., ge=1, le=120, description="Запрашиваемый срок кредита (мес)", examples=[24])
    has_collateral: bool = Field(..., description="Наличие залога (true/false)", examples=[True])
    collateral_value: float = Field(0.0, ge=0, description="Оценочная стоимость залога в рублях (если нет = 0.0)", examples=[1500000.0])


# =====================================================================
# 2. ВЫХОДНОЙ КОНТРАКТ ДАННЫХ (От Python обратно в Kotlin) — 11 полей
# =====================================================================
class ScoringResponse(BaseModel):
    client_id: str
    decision: str                # Строго: "APPROVED", "COUNTER_OFFER", "REJECTED"
    reason: str                  # Понятное текстовое объяснение для клиента и банка
    score: int                   # Итоговый скоринговый балл (0 - 100+)
    risk_grade: str              # Грейд надежности: "A", "B", "C", "D", "E"
    interest_rate: float         # Персональная годовая ставка (%)
    approved_amount: float       # Одобренная сумма (руб)
    approved_term_months: int    # Одобренный срок (мес)
    monthly_payment: float       # Ежемесячный аннуитетный платеж по одобренным условиям (руб)
    dti_ratio: float             # Итоговая долговая нагрузка (доля от чистой прибыли, например 0.42 = 42%)
    profitability_margin: float  # Рентабельность бизнеса по чистой прибыли (%)


# =====================================================================
# 3. ФИНАНСОВАЯ МАТЕМАТИКА (Аннуитетные формулы)
# =====================================================================
def calc_annuity_payment(amount: float, annual_rate: float, term_months: int) -> float:
    """Считает ежемесячный аннуитетный платеж по сумме, годовой ставке и сроку."""
    if amount <= 0 or term_months <= 0:
        return 0.0
    monthly_rate = (annual_rate / 100.0) / 12.0
    if monthly_rate == 0:
        return amount / term_months
    factor = (monthly_rate * math.pow(1 + monthly_rate, term_months)) / (math.pow(1 + monthly_rate, term_months) - 1)
    return amount * factor

def calc_max_amount_from_payment(max_payment: float, annual_rate: float, term_months: int) -> float:
    """Обратная формула аннуитета: считает максимальную сумму кредита под заданный посильный платеж."""
    if max_payment <= 0 or term_months <= 0:
        return 0.0
    monthly_rate = (annual_rate / 100.0) / 12.0
    if monthly_rate == 0:
        return max_payment * term_months
    factor = (monthly_rate * math.pow(1 + monthly_rate, term_months)) / (math.pow(1 + monthly_rate, term_months) - 1)
    return max_payment / factor


# =====================================================================
# 4. ОСНОВНОЙ ЭНДПОИНТ СКОРИНГА И ПРИНЯТИЯ РЕШЕНИЙ
# =====================================================================
@app.post("/api/v1/scoring/evaluate", response_model=ScoringResponse)
def evaluate_application(req: ScoringRequest):
    # Оборачиваем входные данные в Pandas DataFrame для векторных расчетов аналитики
    df = pd.DataFrame([req.model_dump()])
    
    # Вычисляем базовые финансовые метрики компании
    df['net_profit'] = df['monthly_income'] - df['monthly_expenses']
    df['margin'] = np.where(df['monthly_income'] > 0, (df['net_profit'] / df['monthly_income']) * 100.0, 0.0)
    df['free_cash_flow'] = df['net_profit'] - df['current_debts_payment']
    
    net_profit = float(df['net_profit'].iloc[0])
    margin = float(df['margin'].iloc[0])
    free_cash_flow = float(df['free_cash_flow'].iloc[0])

    # -----------------------------------------------------------------
    # ЭТАП 1: Жесткие стоп-факторы (Knock-out rules)
    # -----------------------------------------------------------------
    if net_profit <= 0 or free_cash_flow <= 10000:
        return ScoringResponse(
            client_id=req.client_id, decision="REJECTED",
            reason="Убыточная деятельность или свободный денежный поток после уплаты текущих долгов менее 10 000 руб/мес.",
            score=0, risk_grade="E", interest_rate=0.0, approved_amount=0.0,
            approved_term_months=0, monthly_payment=0.0, dti_ratio=1.0, profitability_margin=round(margin, 2)
        )
        
    if req.credit_history == 'bad' and not req.has_collateral:
        return ScoringResponse(
            client_id=req.client_id, decision="REJECTED",
            reason="Наличие открытых просрочек в БКИ при отсутствии залогового обеспечения.",
            score=10, risk_grade="E", interest_rate=0.0, approved_amount=0.0,
            approved_term_months=0, monthly_payment=0.0, dti_ratio=1.0, profitability_margin=round(margin, 2)
        )

    # Проверка на статус "Молодой бизнес" (ООО < 9 мес, ИП < 3 мес)
    is_young_business = (req.business_type == 'ООО' and req.business_age_months < 9) or \
                        (req.business_type == 'ИП' and req.business_age_months < 3)

    if is_young_business and req.credit_history == 'bad':
        return ScoringResponse(
            client_id=req.client_id, decision="REJECTED",
            reason="Для нового бизнеса критично отсутствие негативной кредитной истории.",
            score=15, risk_grade="E", interest_rate=0.0, approved_amount=0.0,
            approved_term_months=0, monthly_payment=0.0, dti_ratio=1.0, profitability_margin=round(margin, 2)
        )

    # -----------------------------------------------------------------
    # ЭТАП 2: Балльная скоринговая карта (Scorecard)
    # -----------------------------------------------------------------
    score = 30  # Базовый стартовый балл

    # 2.1 Возраст бизнеса
    if is_young_business:
        score -= 10  # Штраф за новизну, но НЕ отказ (перевод в песочницу лимитов)
    elif req.business_age_months < 12:
        score += 5
    elif req.business_age_months <= 36:
        score += 15
    else:
        score += 25

    # 2.2 Кредитная история (БКИ)
    ch_weights = {'good': 25, 'none': 5, 'bad': -30}
    score += ch_weights.get(req.credit_history, 0)

    # 2.3 Покрытие залогом (LTV - Loan to Value)
    if req.has_collateral and req.collateral_value > 0:
        collateral_coverage = req.collateral_value / req.requested_amount
        if collateral_coverage >= 1.2:
            score += 25
        elif collateral_coverage >= 0.7:
            score += 15
        else:
            score += 5
    
    # 2.4 Отраслевой риск по ОКВЭД
    okved_weights = {
        'it': 15, 'production': 15,
        'trade': 10, 'services': 10,
        'horeca': -5, 'construction': -10
    }
    score += okved_weights.get(req.okved_category, 0)

    # 2.5 Рентабельность бизнеса
    if margin >= 25: score += 15
    elif margin >= 10: score += 10
    elif margin >= 5: score += 0
    else: score -= 10

    # -----------------------------------------------------------------
    # ЭТАП 3: Определение Risk Grade, Ставки и Предельного DTI
    # -----------------------------------------------------------------
    if score >= 85:
        grade, base_rate, max_dti_limit = "A", 16.5, 0.60
    elif score >= 65:
        grade, base_rate, max_dti_limit = "B", 18.5, 0.50
    elif score >= 45:
        grade, base_rate, max_dti_limit = "C", 21.0, 0.40
    elif score >= 30:
        grade, base_rate, max_dti_limit = "D", 24.5, 0.30
    else:
        return ScoringResponse(
            client_id=req.client_id, decision="REJECTED",
            reason=f"Недостаточный скоринговый балл ({score} из минимальных 30). Высокий совокупный риск.",
            score=score, risk_grade="E", interest_rate=0.0, approved_amount=0.0,
            approved_term_months=0, monthly_payment=0.0, dti_ratio=1.0, profitability_margin=round(margin, 2)
        )

    # Скидка к ставке -1.5% за 100% покрытие залогом
    if req.has_collateral and req.collateral_value >= req.requested_amount:
        base_rate -= 1.5

    # -----------------------------------------------------------------
    # ЭТАП 4: Проверка долговой нагрузки (DTI) и генерация решения
    # -----------------------------------------------------------------
    req_monthly_payment = calc_annuity_payment(req.requested_amount, base_rate, req.requested_term_months)
    total_projected_debt = req.current_debts_payment + req_monthly_payment
    projected_dti = total_projected_debt / net_profit

    # Потолок суммы для молодого бизнеса (ИП < 3 мес, ООО < 9 мес)
    young_business_cap = 500_000.0 if not req.has_collateral else min(1_500_000.0, req.collateral_value * 0.8)

    # СЦЕНАРИЙ 1: Прямое одобрение (APPROVED)
    if projected_dti <= max_dti_limit and (not is_young_business or req.requested_amount <= young_business_cap):
        return ScoringResponse(
            client_id=req.client_id,
            decision="APPROVED",
            reason="Заявка полностью соответствует критериям финансовой устойчивости.",
            score=score, risk_grade=grade, interest_rate=round(base_rate, 2),
            approved_amount=round(req.requested_amount, 2),
            approved_term_months=req.requested_term_months,
            monthly_payment=round(req_monthly_payment, 2),
            dti_ratio=round(projected_dti, 2),
            profitability_margin=round(margin, 2)
        )

    # СЦЕНАРИЙ 2: Поиск встречного предложения (COUNTER_OFFER)
    max_affordable_new_payment = (net_profit * max_dti_limit) - req.current_debts_payment

    if max_affordable_new_payment <= 5000:
        return ScoringResponse(
            client_id=req.client_id, decision="REJECTED",
            reason="Высокая текущая закредитованность не позволяет выделить лимит под новый платеж.",
            score=score, risk_grade=grade, interest_rate=0.0, approved_amount=0.0,
            approved_term_months=0, monthly_payment=0.0, dti_ratio=round(projected_dti, 2), profitability_margin=round(margin, 2)
        )

    # Попытка А: Растягиваем срок кредита (с шагом 6 мес), чтобы снизить ежемесячный платеж
    max_allowed_term = 18 if is_young_business else 60
    best_term = req.requested_term_months

    for term in range(req.requested_term_months, max_allowed_term + 1, 6):
        test_payment = calc_annuity_payment(req.requested_amount, base_rate, term)
        if test_payment <= max_affordable_new_payment:
            best_term = term
            break

    recalculated_payment = calc_annuity_payment(req.requested_amount, base_rate, best_term)
    if recalculated_payment <= max_affordable_new_payment and (not is_young_business or req.requested_amount <= young_business_cap):
        new_dti = (req.current_debts_payment + recalculated_payment) / net_profit
        return ScoringResponse(
            client_id=req.client_id,
            decision="COUNTER_OFFER",
            reason=f"Для комфортной долговой нагрузки предлагаем увеличить срок кредита с {req.requested_term_months} до {best_term} мес.",
            score=score, risk_grade=grade, interest_rate=round(base_rate, 2),
            approved_amount=round(req.requested_amount, 2),
            approved_term_months=best_term,
            monthly_payment=round(recalculated_payment, 2),
            dti_ratio=round(new_dti, 2),
            profitability_margin=round(margin, 2)
        )

    # Попытка Б: Снижаем саму сумму кредита под максимально допустимый платеж клиента
    safe_amount = calc_max_amount_from_payment(max_affordable_new_payment, base_rate, max_allowed_term)
    
    if is_young_business:
        safe_amount = min(safe_amount, young_business_cap)
        reason_text = "Стартовый предел финансирования для нового бизнеса (ИП < 3 мес / ООО < 9 мес) на основе текущей прибыли."
    else:
        reason_text = "Запрошенная сумма превышает лимит долговой нагрузки. Предлагаем сниженную безопасную сумму."

    # Округление вниз до красивых 10 000 руб.
    safe_amount = math.floor(safe_amount / 10000.0) * 10000.0

    if safe_amount < 50_000:
        return ScoringResponse(
            client_id=req.client_id, decision="REJECTED",
            reason="Рассчитанный безопасный лимит кредитования составляет менее минимальных 50 000 руб.",
            score=score, risk_grade=grade, interest_rate=0.0, approved_amount=0.0,
            approved_term_months=0, monthly_payment=0.0, dti_ratio=round(projected_dti, 2), profitability_margin=round(margin, 2)
        )

    final_payment = calc_annuity_payment(safe_amount, base_rate, max_allowed_term)
    final_dti = (req.current_debts_payment + final_payment) / net_profit

    return ScoringResponse(
        client_id=req.client_id,
        decision="COUNTER_OFFER",
        reason=reason_text,
        score=score, risk_grade=grade, interest_rate=round(base_rate, 2),
        approved_amount=round(safe_amount, 2),
        approved_term_months=max_allowed_term,
        monthly_payment=round(final_payment, 2),
        dti_ratio=round(final_dti, 2),
        profitability_margin=round(margin, 2)
    )

@app.get("/health")
def health_check():
    """Проверка работоспособности контейнера для Docker."""
    return {"status": "ok"}