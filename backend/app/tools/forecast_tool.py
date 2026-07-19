from calendar import monthrange
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Transaction
from app.services.date_utils import month_bounds, today_jst
from app.tools.analytics_tool import query_spending_summary
from app.tools.budget_tool import get_total_budget

VARIABLE_CATEGORIES = {"food", "transport", "shopping", "entertainment", "education", "health", "travel", "social", "other"}


def forecast_month_end(db: Session, user_id: int, month: str) -> dict:
    start, end = month_bounds(month)
    today = today_jst()
    effective_today = min(max(today, start), end)
    elapsed_days = max((effective_today - start).days + 1, 1)
    total_days = monthrange(start.year, start.month)[1]
    remaining_days = max((end - effective_today).days, 0)

    summary = query_spending_summary(db, user_id, start, effective_today)
    current_spending = summary["total_expense"]

    fixed_costs = int(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.is_fixed.is_(True),
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= effective_today,
        )
        .scalar()
        or 0
    )
    variable_spending = int(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.is_fixed.is_(False),
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= effective_today,
        )
        .scalar()
        or 0
    )

    recent_start = max(start, effective_today - timedelta(days=13))
    recent_days = max((effective_today - recent_start).days + 1, 1)
    recent_variable = int(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.is_fixed.is_(False),
            Transaction.transaction_date >= recent_start,
            Transaction.transaction_date <= effective_today,
        )
        .scalar()
        or 0
    )
    enough_recent_data = recent_days >= 7 and recent_variable > 0
    daily_variable = recent_variable / recent_days if enough_recent_data else variable_spending / elapsed_days

    expected = round(fixed_costs + variable_spending + daily_variable * remaining_days)
    optimistic = round(fixed_costs + variable_spending + daily_variable * 0.85 * remaining_days)
    pessimistic = round(fixed_costs + variable_spending + daily_variable * 1.15 * remaining_days)

    budget = get_total_budget(db, user_id, month)
    over_budget = expected - budget if budget is not None else None
    risk_level = "unknown"
    if budget:
        ratio = expected / budget
        if ratio > 1.15:
            risk_level = "critical"
        elif ratio > 1:
            risk_level = "high"
        elif ratio >= 0.85:
            risk_level = "medium"
        else:
            risk_level = "low"

    return {
        "month": month,
        "current_spending": current_spending,
        "predicted_month_end_spending": expected,
        "optimistic": optimistic,
        "pessimistic": pessimistic,
        "monthly_budget": budget,
        "predicted_over_budget": over_budget,
        "risk_level": risk_level,
        "confidence": "medium" if enough_recent_data else "low",
        "remaining_days": remaining_days,
    }
