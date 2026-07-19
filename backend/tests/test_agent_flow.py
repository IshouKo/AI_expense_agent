import os
from pathlib import Path

test_db = Path(__file__).with_name("test_expense_agent.db")
if test_db.exists():
    test_db.unlink()
os.environ["EXPENSE_DATABASE_URL"] = f"sqlite:///{test_db}"

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_agent_records_transaction_and_summarizes():
    response = client.post("/api/v1/agent/chat", json={"message": "今天午饭吃拉面花了980日元"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "ADD_TRANSACTION"
    assert body["data"]["amount"] == 980
    assert body["data"]["category"] == "food"

    summary = client.get("/api/v1/analytics/summary")
    assert summary.status_code == 200
    assert summary.json()["total_expense"] >= 980


def test_budget_and_forecast():
    response = client.post("/api/v1/agent/chat", json={"message": "这个月总预算设置为12万日元"})
    assert response.status_code == 200
    assert response.json()["intent"] == "SET_BUDGET"

    forecast = client.get("/api/v1/forecast/2026-07")
    assert forecast.status_code == 200
    assert forecast.json()["monthly_budget"] == 120000
