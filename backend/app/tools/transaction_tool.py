from datetime import date

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import Transaction
from app.schemas import TransactionCreate, TransactionUpdate


def add_transaction(db: Session, user_id: int, payload: TransactionCreate) -> Transaction:
    transaction = Transaction(user_id=user_id, **payload.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def list_transactions(
    db: Session,
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    category: str | None = None,
    query: str | None = None,
) -> list[Transaction]:
    q = db.query(Transaction).filter(Transaction.user_id == user_id)
    if start_date:
        q = q.filter(Transaction.transaction_date >= start_date)
    if end_date:
        q = q.filter(Transaction.transaction_date <= end_date)
    if category:
        q = q.filter(Transaction.category == category)
    if query:
        like = f"%{query}%"
        q = q.filter((Transaction.note.ilike(like)) | (Transaction.merchant.ilike(like)))
    return q.order_by(desc(Transaction.transaction_date), desc(Transaction.id)).all()


def update_transaction(db: Session, user_id: int, transaction_id: int, payload: TransactionUpdate) -> Transaction | None:
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == user_id).first()
    if not transaction:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(transaction, key, value)
    db.commit()
    db.refresh(transaction)
    return transaction


def delete_transaction(db: Session, user_id: int, transaction_id: int) -> bool:
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == user_id).first()
    if not transaction:
        return False
    db.delete(transaction)
    db.commit()
    return True
