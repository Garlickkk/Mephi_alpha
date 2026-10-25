"""Правила скоринговой карты и встречного предложения (функция evaluate_scoring)."""
import random

import pytest
from conftest import scoring_input

from main import calc_annuity_payment, evaluate_scoring


def test_approved_uses_application_rate():
    r = evaluate_scoring(scoring_input())
    assert r.decision == "APPROVED"
    assert r.interest_rate == 12.5
    assert r.monthly_payment == pytest.approx(calc_annuity_payment(800_000, 12.5, 36), abs=0.01)


def test_collateral_does_not_change_score_or_rate():
    without = evaluate_scoring(scoring_input())
    with_collateral = evaluate_scoring(scoring_input(has_collateral=True, collateral_value=5_000_000))
    assert with_collateral.score == without.score
    assert with_collateral.interest_rate == 12.5


def test_bad_history_needs_collateral_covering_loan():
    short = evaluate_scoring(scoring_input(credit_history="bad", has_collateral=True, collateral_value=500_000))
    assert short.decision == "REJECTED"
    covered = evaluate_scoring(scoring_input(credit_history="bad", has_collateral=True, collateral_value=1_000_000))
    assert covered.score is not None


def test_stop_factor_rejection_has_no_fake_metrics():
    r = evaluate_scoring(scoring_input(monthly_expenses=3_100_000))
    assert r.decision == "REJECTED"
    assert r.score is None and r.interest_rate is None and r.monthly_payment is None and r.approved_amount is None


def test_small_profitable_business_is_not_cut_by_absolute_threshold():
    r = evaluate_scoring(scoring_input(monthly_income=100_000, monthly_expenses=90_000, current_debts_payment=2_000,
                                       requested_amount=100_000, requested_term_years=2))
    assert r.decision != "REJECTED"


def test_counter_offer_term_within_product():
    r = evaluate_scoring(scoring_input(requested_amount=20_000_000, requested_term_years=1, product_max_term_years=3,
                                       product_min_sum=50_000, product_max_sum=30_000_000))
    assert r.decision == "COUNTER_OFFER"
    assert r.approved_term_months <= 36


def test_safe_amount_below_product_min_is_rejected():
    r = evaluate_scoring(scoring_input(requested_amount=60_000_000, requested_term_years=1, product_max_term_years=2,
                                       product_min_sum=40_000_000, product_max_sum=60_000_000))
    assert r.decision == "REJECTED"


def test_long_requested_term_is_not_shortened():
    r = evaluate_scoring(scoring_input(requested_amount=80_000_000, requested_term_years=7, product_max_term_years=10,
                                       product_max_sum=100_000_000))
    assert r.decision == "COUNTER_OFFER"
    assert r.approved_term_months >= 84


def test_invariants_on_random_applications():
    """Ставка = ставке заявки, срок в целых годах, платёж соответствует условиям, встречное в пределах продукта."""
    rng = random.Random(1)
    for _ in range(5_000):
        young = rng.random() < 0.15
        btype = rng.choice(["ООО", "ИП"])
        age = rng.randint(0, 8) if young else rng.randint(9, 200)
        pmax_y = rng.choice([None, 2, 3, 5, 7, 10])
        req_y = rng.randint(1, pmax_y or 10)
        pmin, pmax = rng.choice([(None, None), (50_000, 5_000_000), (1_000_000, 50_000_000), (100_000, 150_000_000)])
        amount = rng.uniform(pmin or 50_000, pmax or 100_000_000)
        coll = rng.random() < 0.4
        inc = rng.uniform(100_000, 6_000_000)
        inp = scoring_input(
            business_type=btype, business_age_months=age,
            okved_category=rng.choice(["it", "trade", "production", "services", "construction", "horeca"]),
            monthly_income=inc, monthly_expenses=inc * rng.uniform(0.5, 1.05),
            current_debts_payment=inc * rng.uniform(0, 0.15), credit_history=rng.choice(["good", "none", "bad"]),
            requested_amount=amount, requested_term_years=req_y, annual_rate=rng.uniform(8, 30), has_collateral=coll,
            collateral_value=rng.uniform(0, 3) * amount if coll else 0.0,
            product_min_sum=pmin, product_max_sum=pmax, product_max_term_years=pmax_y)
        r = evaluate_scoring(inp)
        ctx = f"{inp.model_dump()} -> {r.model_dump()}"
        if r.decision == "REJECTED":
            assert r.interest_rate is None and r.monthly_payment is None and r.approved_amount is None, ctx
            continue
        years = r.approved_term_months / 12
        assert r.interest_rate == round(inp.annual_rate, 2), ctx
        assert years == int(years), ctx
        expected_payment = calc_annuity_payment(r.approved_amount, inp.annual_rate, r.approved_term_months)
        assert abs(expected_payment - r.monthly_payment) <= 0.02, ctx
        if pmax_y is not None:
            assert years <= pmax_y, ctx
        if r.decision == "COUNTER_OFFER":
            is_young = (btype == "ООО" and age < 9) or (btype == "ИП" and age < 3)
            if not is_young:
                assert years >= req_y, ctx
            if pmin is not None:
                assert r.approved_amount >= pmin, ctx
            if pmax is not None:
                assert r.approved_amount <= pmax, ctx
            assert not (r.approved_amount == round(amount, 2) and years == req_y), ctx
