"""HTTP-контракт с application_server: решения, ошибки, идемпотентность, ручная проверка и callback."""
import time

import pytest
from conftest import PRODUCT, TOKEN, decision_body, post_decision

import main

DEMO_CASES = [
    ("7700000001", 3_000_000, 3, False, "APPROVED"),
    ("7700000002", 3_000_000, 2, False, "COUNTER_OFFER"),
    ("7700000003", 3_000_000, 3, False, "COUNTER_OFFER"),
    ("7700000004", 1_000_000, 3, False, "REJECTED"),
    ("7700000005", 3_000_000, 3, True, "PENDING"),
]


@pytest.mark.parametrize("inn,amount,years,collateral,outcome", DEMO_CASES)
def test_demo_clients(client, inn, amount, years, collateral, outcome):
    resp = post_decision(client, inn=inn, amount=amount, years=years, collateral=collateral)
    assert resp.json()["outcome"] == outcome, resp.json()
    assert resp.status_code == (202 if outcome == "PENDING" else 200)


@pytest.mark.parametrize("okved", ["47.11", "41.20", "56.10", "70.22"])
@pytest.mark.parametrize("reg", ["2023-01-10", "2015-06-01"])
def test_demo_clients_1_to_4_do_not_depend_on_okved_and_age(client, okved, reg):
    for inn, amount, years, collateral, outcome in DEMO_CASES[:4]:
        resp = post_decision(client, inn=inn, amount=amount, years=years, collateral=collateral, okved=okved, reg=reg)
        assert resp.json()["outcome"] == outcome


def test_counter_offer_has_null_for_unchanged_fields(client):
    co = post_decision(client, inn="7700000002", amount=3_000_000, years=2).json()["counterOffer"]
    assert co == {"rate": None, "amount": None, "durationYears": 4}


def test_response_rate_is_product_rate(client):
    body = post_decision(client, amount=800_000, years=3).json()
    assert body["interestRate"] == 12.5


def test_product_limits_violation_is_400(client):
    resp = post_decision(client, amount=5_000_000, years=3)
    assert resp.status_code == 400
    assert set(resp.json()) == {"message", "dateTime"}


def test_validation_error_is_400_with_common_error_format(client):
    resp = client.post("/api/v1/decisions", json={"applicationId": 1}, headers={**TOKEN, "Idempotency-Key": "1"})
    assert resp.status_code == 400
    assert set(resp.json()) == {"message", "dateTime"}


def test_missing_token_is_403_even_with_invalid_body(client):
    resp = client.post("/api/v1/decisions", json={}, headers={"Idempotency-Key": "1"})
    assert resp.status_code == 403
    assert "message" in resp.json()


def test_idempotency(client):
    first = post_decision(client, inn="7712345678", app_id=7001)
    repeat = post_decision(client, inn="7712345678", app_id=7001)
    assert repeat.json() == first.json()
    changed = post_decision(client, inn="7712345678", amount=900_000, app_id=7001)
    assert changed.status_code == 409


def test_manual_review_triggers():
    assert main.manual_review_reason(main.ScoringResult(
        decision="APPROVED", reason="x", risk_grade="A", approved_amount=40_000_000)) is not None
    assert main.manual_review_reason(main.ScoringResult(decision="REJECTED", reason="x", risk_grade="D")) is None


def test_manual_review_flow_with_callback(client, callbacks):
    resp = post_decision(client, inn="7700000005", amount=3_000_000, years=3, collateral=True, app_id=9001)
    assert resp.status_code == 202
    decision_id = resp.json()["decisionId"]

    queue = client.get("/api/v1/decisions", params={"status": "PENDING"}, headers=TOKEN).json()
    assert any(d["decisionId"] == decision_id for d in queue)
    item = client.get(f"/api/v1/decisions/{decision_id}", headers=TOKEN).json()
    assert item["manualReviewReason"] and item["recommendation"]["outcome"] == "COUNTER_OFFER"

    resp = client.post(f"/api/v1/decisions/{decision_id}/resolve", json={"outcome": "COUNTER_OFFER"}, headers=TOKEN)
    assert resp.status_code == 200
    assert resp.json()["response"]["counterOffer"] == item["recommendation"]["counterOffer"]

    for _ in range(50):
        status = client.get(f"/api/v1/decisions/{decision_id}", headers=TOKEN).json()["callbackStatus"]
        if status != "IN_PROGRESS":
            break
        time.sleep(0.1)
    assert status == "DELIVERED"
    path, token, payload = next(c for c in callbacks if c[0].endswith("/9001/decision"))
    assert token == main.SERVICE_TOKEN
    assert payload["outcome"] == "COUNTER_OFFER" and payload["decisionId"] == decision_id

    assert client.post(f"/api/v1/decisions/{decision_id}/resolve", json={"outcome": "APPROVED"},
                       headers=TOKEN).status_code == 409
    final = post_decision(client, inn="7700000005", amount=3_000_000, years=3, collateral=True, app_id=9001)
    assert final.status_code == 200 and final.json()["outcome"] == "COUNTER_OFFER"


def test_outcome_mix_on_mocks():
    """Моки дают все исходы в разумных долях: демо не превращается в «всё одобрено»."""
    import random
    rng = random.Random(7)
    counts = {}
    for i in range(3_000):
        if rng.random() < 0.6:
            amount, years, product, rate = rng.choice([300_000, 1_000_000, 3_000_000]), rng.randint(1, 5), PRODUCT, 12.5
        else:
            amount, years, product, rate = rng.choice([3_000_000, 10_000_000, 20_000_000]), rng.randint(1, 7), None, 18.0
        req = main.DecisionRequest.model_validate(decision_body(
            inn=str(rng.randint(10**9, 10**10 - 1)), amount=amount, years=years, product=product, rate=rate,
            reg=f"{rng.randint(2010, 2025)}-01-01", collateral=rng.random() < 0.3, app_id=i))
        r = main.evaluate_scoring(main.to_scoring_input(req))
        outcome = "PENDING" if main.manual_review_reason(r) else r.decision
        counts[outcome] = counts.get(outcome, 0) + 1
    shares = {k: v / 3_000 for k, v in counts.items()}
    assert 0.3 < shares["APPROVED"] < 0.65
    assert 0.2 < shares["COUNTER_OFFER"] < 0.55
    assert 0.08 < shares["REJECTED"] < 0.3
