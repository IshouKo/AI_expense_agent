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
    assert body["data"]["agent"]["tool"] == "add_transaction"
    assert body["data"]["agent"]["plan"]
    assert body["data"]["agent"]["rag"]["mode"] == "local_keyword_rag"
    assert "fallback" in body["data"]["agent"]["reasoning"]

    summary = client.get("/api/v1/analytics/summary")
    assert summary.status_code == 200
    assert summary.json()["total_expense"] >= 980


def test_budget_and_forecast():
    response = client.post("/api/v1/agent/chat", json={"message": "这个月总预算设置为12万日元"})
    assert response.status_code == 200
    assert response.json()["intent"] == "SET_BUDGET"
    assert response.json()["data"]["agent"]["memory"]["turns_loaded"] >= 1

    forecast = client.get("/api/v1/forecast/2026-07")
    assert forecast.status_code == 200
    assert forecast.json()["monthly_budget"] == 120000


def test_rag_retrieves_prior_transaction_context():
    client.post("/api/v1/agent/chat", json={"message": "昨天在Amazon买书花了3280日元"})

    response = client.post("/api/v1/agent/chat", json={"message": "Amazon相关的支出能查到吗"})
    assert response.status_code == 200
    rag = response.json()["data"]["agent"]["rag"]
    assert rag["documents_retrieved"] >= 1
    assert "transaction" in rag["sources"] or "agent_log" in rag["sources"]
