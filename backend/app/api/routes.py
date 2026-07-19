import csv
from datetime import date
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.agents.orchestrator import handle_chat
from app.core.database import get_db
from app.repositories.user_repository import get_or_create_default_user
from app.schemas import AgentChatRequest, AgentChatResponse, BudgetCreate, BudgetRead, ForecastResponse, SummaryResponse, TransactionCreate, TransactionRead, TransactionUpdate
from app.services.date_utils import current_month, month_bounds, previous_month_same_span, today_jst
from app.tools.advice_tool import generate_spending_advice
from app.tools.analytics_tool import compare_periods, daily_trend, query_spending_summary
from app.tools.budget_tool import get_budgets, set_budget
from app.tools.forecast_tool import forecast_month_end
from app.tools.transaction_tool import add_transaction, delete_transaction, list_transactions, update_transaction

router = APIRouter(prefix="/api/v1")


@router.post("/agent/chat", response_model=AgentChatResponse)
def agent_chat(payload: AgentChatRequest, db: Session = Depends(get_db)):
    return handle_chat(db, payload.message)


@router.get("/transactions", response_model=list[TransactionRead])
def get_transactions(start_date: date | None = None, end_date: date | None = None, category: str | None = None, q: str | None = None, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    return list_transactions(db, user.id, start_date, end_date, category, q)


@router.post("/transactions", response_model=TransactionRead)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    return add_transaction(db, user.id, payload)


@router.patch("/transactions/{transaction_id}", response_model=TransactionRead)
def patch_transaction(transaction_id: int, payload: TransactionUpdate, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    transaction = update_transaction(db, user.id, transaction_id, payload)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.delete("/transactions/{transaction_id}")
def remove_transaction(transaction_id: int, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    if not delete_transaction(db, user.id, transaction_id):
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"ok": True}


@router.get("/analytics/summary", response_model=SummaryResponse)
def summary(start_date: date | None = None, end_date: date | None = None, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    if not start_date or not end_date:
        start_date, end_date = month_bounds(current_month())
    return query_spending_summary(db, user.id, start_date, end_date)


@router.get("/analytics/categories")
def categories(month: str | None = None, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    start, end = month_bounds(month or current_month())
    return query_spending_summary(db, user.id, start, end)["by_category"]


@router.get("/analytics/trend")
def trend(month: str | None = None, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    start, end = month_bounds(month or current_month())
    return daily_trend(db, user.id, start, min(end, today_jst()))


@router.get("/analytics/compare")
def compare(month: str | None = None, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    start, end = month_bounds(month or current_month())
    effective_end = min(end, today_jst())
    previous_start, previous_end = previous_month_same_span(start, effective_end)
    return compare_periods(db, user.id, start, effective_end, previous_start, previous_end)


@router.get("/budgets/{month}", response_model=list[BudgetRead])
def budgets(month: str, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    return get_budgets(db, user.id, month)


@router.post("/budgets", response_model=BudgetRead)
def create_budget(payload: BudgetCreate, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    return set_budget(db, user.id, payload)


@router.get("/forecast/{month}", response_model=ForecastResponse)
def forecast(month: str, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    return forecast_month_end(db, user.id, month)


@router.post("/advice/generate")
def advice(month: str | None = None, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    return generate_spending_advice(db, user.id, month or current_month())


@router.get("/alerts")
def alerts(db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    advice_result = generate_spending_advice(db, user.id, current_month())
    return {"alerts": advice_result["suggestions"]}


@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    transactions = list_transactions(db, user.id)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "type", "amount", "currency", "category", "merchant", "note", "transaction_date", "is_fixed"])
    for tx in transactions:
        writer.writerow([tx.id, tx.type, tx.amount, tx.currency, tx.category, tx.merchant, tx.note, tx.transaction_date, tx.is_fixed])
    return Response(content=buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=transactions.csv"})
