from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.agents.parser import parse_budget, parse_transaction
from app.services.date_utils import current_month, month_bounds, previous_month_same_span, today_jst, week_bounds
from app.tools.advice_tool import generate_spending_advice
from app.tools.analytics_tool import compare_periods, query_spending_summary, top_transactions
from app.tools.budget_tool import set_budget
from app.tools.forecast_tool import forecast_month_end
from app.tools.transaction_tool import add_transaction


TOOL_DESCRIPTIONS = {
    "add_transaction": "Record one expense or income transaction after extracting amount, category, date, merchant, and note.",
    "set_budget": "Create or update a monthly total/category budget.",
    "query_spending_summary": "Summarize income, expenses, net amount, and category totals for a period.",
    "compare_periods": "Compare this month with the equivalent span in the previous month.",
    "forecast_month_end": "Forecast month-end spending and budget-overrun risk.",
    "generate_spending_advice": "Generate budget control advice from current spending.",
    "top_transactions": "Find the largest transactions in a period.",
}


def execute_tool(db: Session, user_id: int, tool_name: str, message: str, extracted_transaction=None) -> dict[str, Any]:
    if tool_name == "set_budget":
        payload = parse_budget(message)
        if not payload:
            return {"ok": False, "error": "missing_amount", "tool_input": None, "data": {}}
        budget = set_budget(db, user_id, payload)
        return {
            "ok": True,
            "tool_input": payload.model_dump(),
            "data": {"budget_id": budget.id, "month": budget.month, "category": budget.category, "amount": budget.amount},
        }
    if tool_name == "query_spending_summary":
        start, end = period_from_message(message)
        data = query_spending_summary(db, user_id, start, end)
        return {"ok": True, "tool_input": {"start_date": str(start), "end_date": str(end)}, "data": data}
    if tool_name == "compare_periods":
        start, end = month_bounds(current_month())
        effective_end = min(end, today_jst())
        previous_start, previous_end = previous_month_same_span(start, effective_end)
        data = compare_periods(db, user_id, start, effective_end, previous_start, previous_end)
        return {"ok": True, "tool_input": {"current_start": str(start), "current_end": str(effective_end)}, "data": data}
    if tool_name == "forecast_month_end":
        data = forecast_month_end(db, user_id, current_month())
        return {"ok": True, "tool_input": {"month": current_month()}, "data": data}
    if tool_name == "generate_spending_advice":
        data = generate_spending_advice(db, user_id, current_month())
        return {"ok": True, "tool_input": {"month": current_month()}, "data": data}
    if tool_name == "top_transactions":
        start, end = period_from_message(message)
        txs = top_transactions(db, user_id, start, end, 3)
        data = {"transactions": [{"id": t.id, "amount": t.amount, "category": t.category, "note": t.note, "merchant": t.merchant} for t in txs]}
        return {"ok": True, "tool_input": {"start_date": str(start), "end_date": str(end)}, "data": data}
    if tool_name == "add_transaction":
        payload = extracted_transaction or parse_transaction(message)
        if not payload:
            return {"ok": False, "error": "unsupported", "tool_input": None, "data": {}}
        tx = add_transaction(db, user_id, payload)
        return {
            "ok": True,
            "tool_input": payload.model_dump(mode="json"),
            "data": {"transaction_id": tx.id, "amount": tx.amount, "category": tx.category, "confidence": tx.confidence},
        }
    return {"ok": False, "error": "unsupported_tool", "tool_input": None, "data": {}}


def period_from_message(message: str):
    if "今日" in message or "今天" in message:
        day = today_jst()
        return day, day
    if "今週" in message or "本周" in message or "这周" in message:
        return week_bounds()
    if "最近30日" in message or "最近30天" in message:
        end = today_jst()
        return end - timedelta(days=29), end
    return month_bounds(current_month())
