from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


TransactionType = Literal["expense", "income"]


class TransactionBase(BaseModel):
    type: TransactionType = "expense"
    amount: int = Field(ge=0)
    currency: str = "JPY"
    category: str = "other"
    merchant: str | None = None
    note: str | None = None
    transaction_date: date
    source: str = "manual"
    is_fixed: bool = False
    confidence: float | None = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    type: TransactionType | None = None
    amount: int | None = Field(default=None, ge=0)
    currency: str | None = None
    category: str | None = None
    merchant: str | None = None
    note: str | None = None
    transaction_date: date | None = None
    is_fixed: bool | None = None


class TransactionRead(TransactionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BudgetCreate(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    category: str | None = None
    amount: int = Field(ge=0)


class BudgetRead(BudgetCreate):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentChatRequest(BaseModel):
    message: str


class AgentChatResponse(BaseModel):
    intent: str
    message: str
    data: dict


class SummaryResponse(BaseModel):
    start_date: date
    end_date: date
    total_expense: int
    total_income: int
    net: int
    by_category: list[dict]


class ForecastResponse(BaseModel):
    month: str
    current_spending: int
    predicted_month_end_spending: int
    optimistic: int
    pessimistic: int
    monthly_budget: int | None
    predicted_over_budget: int | None
    risk_level: str
    confidence: str
    remaining_days: int


class AdviceRequest(BaseModel):
    month: str
