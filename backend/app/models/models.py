from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str | None]
    default_currency: Mapped[str] = mapped_column(default="JPY")
    timezone: Mapped[str] = mapped_column(default="Asia/Tokyo")
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("type IN ('expense', 'income')"),
        CheckConstraint("amount >= 0"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str]
    amount: Mapped[int]
    currency: Mapped[str] = mapped_column(default="JPY")
    category: Mapped[str]
    merchant: Mapped[str | None]
    note: Mapped[str | None]
    transaction_date: Mapped[date]
    source: Mapped[str] = mapped_column(default="manual")
    is_fixed: Mapped[bool] = mapped_column(default=False)
    confidence: Mapped[float | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    user: Mapped[User] = relationship(back_populates="transactions")


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("user_id", "month", "category"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    month: Mapped[str]
    category: Mapped[str | None]
    amount: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class SavingGoal(Base):
    __tablename__ = "saving_goals"
    __table_args__ = (UniqueConstraint("user_id", "month"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    month: Mapped[str]
    target_amount: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str]
    amount: Mapped[int]
    category: Mapped[str]
    merchant: Mapped[str | None]
    recurrence_rule: Mapped[str]
    next_date: Mapped[date | None]
    active: Mapped[bool] = mapped_column(default=True)


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user_message: Mapped[str]
    detected_intent: Mapped[str | None]
    tool_name: Mapped[str | None]
    tool_input: Mapped[str | None]
    tool_output: Mapped[str | None]
    success: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())
