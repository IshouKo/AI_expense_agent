from datetime import date, timedelta

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models import Transaction


def query_spending_summary(db: Session, user_id: int, start_date: date, end_date: date) -> dict:
    totals = (
        db.query(
            func.coalesce(func.sum(case((Transaction.type == "expense", Transaction.amount), else_=0)), 0),
            func.coalesce(func.sum(case((Transaction.type == "income", Transaction.amount), else_=0)), 0),
        )
        .filter(Transaction.user_id == user_id, Transaction.transaction_date >= start_date, Transaction.transaction_date <= end_date)
        .one()
    )
    by_category = (
        db.query(Transaction.category, func.coalesce(func.sum(Transaction.amount), 0).label("amount"))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )
    total_expense = int(totals[0] or 0)
    total_income = int(totals[1] or 0)
    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_expense": total_expense,
        "total_income": total_income,
        "net": total_income - total_expense,
        "by_category": [{"category": row.category, "amount": int(row.amount)} for row in by_category],
    }


def daily_trend(db: Session, user_id: int, start_date: date, end_date: date) -> list[dict]:
    rows = (
        db.query(Transaction.transaction_date, func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        .group_by(Transaction.transaction_date)
        .all()
    )
    lookup = {row[0]: int(row[1]) for row in rows}
    days = (end_date - start_date).days + 1
    return [{"date": start_date + timedelta(days=i), "amount": lookup.get(start_date + timedelta(days=i), 0)} for i in range(days)]


def top_transactions(db: Session, user_id: int, start_date: date, end_date: date, limit: int = 3) -> list[Transaction]:
    return (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        .order_by(Transaction.amount.desc())
        .limit(limit)
        .all()
    )


def compare_periods(
    db: Session,
    user_id: int,
    current_start: date,
    current_end: date,
    previous_start: date,
    previous_end: date,
) -> dict:
    current = query_spending_summary(db, user_id, current_start, current_end)
    previous = query_spending_summary(db, user_id, previous_start, previous_end)
    previous_by_category = {item["category"]: item["amount"] for item in previous["by_category"]}
    changes = []
    for item in current["by_category"]:
        old_amount = previous_by_category.pop(item["category"], 0)
        difference = item["amount"] - old_amount
        growth_rate = None if old_amount == 0 else round(difference / old_amount, 4)
        changes.append(
            {
                "category": item["category"],
                "current": item["amount"],
                "previous": old_amount,
                "difference": difference,
                "growth_rate": growth_rate,
            }
        )
    for category, old_amount in previous_by_category.items():
        changes.append({"category": category, "current": 0, "previous": old_amount, "difference": -old_amount, "growth_rate": -1})
    changes.sort(key=lambda item: item["difference"], reverse=True)
    return {
        "current": current,
        "previous": previous,
        "difference": current["total_expense"] - previous["total_expense"],
        "category_changes": changes,
        "large_transactions": [
            {"id": t.id, "amount": t.amount, "category": t.category, "merchant": t.merchant, "note": t.note}
            for t in top_transactions(db, user_id, current_start, current_end, 5)
        ],
    }
