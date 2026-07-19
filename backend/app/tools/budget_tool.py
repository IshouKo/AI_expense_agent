from sqlalchemy.orm import Session

from app.models import Budget
from app.schemas import BudgetCreate


def set_budget(db: Session, user_id: int, payload: BudgetCreate) -> Budget:
    budget = (
        db.query(Budget)
        .filter(Budget.user_id == user_id, Budget.month == payload.month, Budget.category == payload.category)
        .first()
    )
    if budget:
        budget.amount = payload.amount
    else:
        budget = Budget(user_id=user_id, **payload.model_dump())
        db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def get_budgets(db: Session, user_id: int, month: str) -> list[Budget]:
    return db.query(Budget).filter(Budget.user_id == user_id, Budget.month == month).order_by(Budget.category.asc()).all()


def get_total_budget(db: Session, user_id: int, month: str) -> int | None:
    budget = db.query(Budget).filter(Budget.user_id == user_id, Budget.month == month, Budget.category.is_(None)).first()
    return budget.amount if budget else None
