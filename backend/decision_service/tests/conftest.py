import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

# Фейковый application_server: принимает callback'и решений, поднимается до импорта main,
# чтобы сервис взял его адрес из APPLICATION_SERVICE_URL
received_callbacks: list[tuple[str, str, dict]] = []


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        received_callbacks.append((self.path, self.headers.get("X-Service-Token"), body))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):
        pass


_server = HTTPServer(("127.0.0.1", 0), _CallbackHandler)
threading.Thread(target=_server.serve_forever, daemon=True).start()
os.environ["APPLICATION_SERVICE_URL"] = f"http://127.0.0.1:{_server.server_port}"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

TOKEN = {"X-Service-Token": main.SERVICE_TOKEN}
PRODUCT = {"id": 1, "title": "Потребительский кредит", "interest": 12.5, "discountInterest": 10.5, "minSum": 50000,
           "maxSum": 3000000, "minDurationYear": 1, "maxDurationYear": 5, "repaymentTypes": ["EQUAL_TOTAL_PARTS"],
           "mainDifference": "Без залога и поручителей"}


@pytest.fixture(scope="session")
def client():
    return TestClient(main.app)


@pytest.fixture
def callbacks():
    return received_callbacks


_next_id = [1000]


def decision_body(inn="7701234567", amount=800_000, years=3, collateral=False, product=PRODUCT, rate=12.5,
                  reg="2019-03-01", okved="62.01", org="OOO", app_id=None):
    if app_id is None:
        _next_id[0] += 1
        app_id = _next_id[0]
    return {"applicationId": app_id,
            "client": {"inn": inn, "organizationType": org, "okvedMain": okved, "registrationDate": reg},
            "loan": {"rate": rate, "amount": amount, "durationYears": years, "purpose": "Пополнение оборотных средств",
                     "collateral": collateral},
            "product": product, "requestedAt": "2026-10-26T10:00:00Z"}


def post_decision(client, **kwargs):
    body = decision_body(**kwargs)
    return client.post("/api/v1/decisions", json=body,
                       headers={**TOKEN, "Idempotency-Key": str(body["applicationId"])})


def scoring_input(**overrides):
    values = dict(client_id="7701234567", business_type="ООО", business_age_months=48, okved_category="it",
                  monthly_income=3_000_000, monthly_expenses=2_000_000, current_debts_payment=100_000,
                  credit_history="good", requested_amount=800_000, requested_term_years=3, annual_rate=12.5,
                  has_collateral=False, collateral_value=0.0)
    values.update(overrides)
    return main.ScoringInput(**values)
