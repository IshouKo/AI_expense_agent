from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.agents.rag import format_rag_context
from app.schemas import BudgetCreate, TransactionCreate
from app.services.categories import categorize
from app.services.date_utils import current_month, today_jst


Category = Literal[
    "food",
    "transport",
    "shopping",
    "entertainment",
    "education",
    "health",
    "housing",
    "subscription",
    "travel",
    "social",
    "salary",
    "reimbursement",
    "other",
]


class TransactionExtraction(BaseModel):
    is_transaction: bool
    type: Literal["expense", "income"] = "expense"
    amount: int | None = Field(default=None, ge=0)
    currency: str = "JPY"
    category: Category = "other"
    merchant: str | None = None
    note: str | None = None
    transaction_date: date | None = None
    is_fixed: bool = False
    confidence: float = Field(default=0.0, ge=0, le=1)


class ToolDecision(BaseModel):
    intent: Literal[
        "ADD_TRANSACTION",
        "SET_BUDGET",
        "QUERY_SUMMARY",
        "COMPARE_PERIOD",
        "FORECAST_SPENDING",
        "GENERATE_ADVICE",
        "QUERY_TOP",
        "UNKNOWN",
    ]
    tool_name: Literal[
        "add_transaction",
        "set_budget",
        "query_spending_summary",
        "compare_periods",
        "forecast_month_end",
        "generate_spending_advice",
        "top_transactions",
        "none",
    ]
    reasoning_summary: str
    confidence: float = Field(ge=0, le=1)


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.enabled = bool(self.settings.openai_api_key)
        self._client = None
        if self.enabled:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self.settings.openai_api_key)
            except Exception:
                self.enabled = False

    def extract_transaction(self, message: str, memory: list[dict], rag_context: dict | None = None) -> TransactionCreate | None:
        if not self.enabled or self._client is None:
            return None
        result = self._parse(
            TransactionExtraction,
            "Extract one expense/income transaction from Japanese or Chinese user text. "
            "Return is_transaction=false when no concrete amount exists. Use JPY unless the user says otherwise.",
            message,
            memory,
            rag_context,
        )
        if not result or not result.is_transaction or result.amount is None:
            return None
        category = result.category or categorize(message)
        return TransactionCreate(
            type=result.type,
            amount=result.amount,
            currency=result.currency or "JPY",
            category=category,
            merchant=result.merchant,
            note=result.note or message,
            transaction_date=result.transaction_date or today_jst(),
            source="agent_llm",
            is_fixed=result.is_fixed,
            confidence=result.confidence,
        )

    def decide_tool(self, message: str, memory: list[dict], rag_context: dict | None = None) -> ToolDecision | None:
        if not self.enabled or self._client is None:
            return None
        memory_text = "\n".join(
            f"- {item.get('user_message')}: intent={item.get('intent')}, tool={item.get('tool_name')}"
            for item in memory[-5:]
        )
        rag_text = format_rag_context(rag_context or {})
        try:
            completion = self._client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Select exactly one finance function to call. Do not answer directly. "
                        "Use the function that best matches the user's message.",
                    },
                    {"role": "system", "content": f"Today is {today_jst().isoformat()}. Current month is {current_month()}."},
                    {"role": "system", "content": f"Recent memory:\n{memory_text or '(none)'}"},
                    {"role": "system", "content": f"Retrieved RAG context:\n{rag_text}"},
                    {"role": "user", "content": message},
                ],
                tools=_function_tools(),
                tool_choice="auto",
            )
            calls = completion.choices[0].message.tool_calls or []
            if not calls:
                return ToolDecision(intent="UNKNOWN", tool_name="none", reasoning_summary="No tool call selected.", confidence=0)
            tool_name = calls[0].function.name
            return ToolDecision(
                intent=_intent_for_tool(tool_name),
                tool_name=tool_name,
                reasoning_summary=f"Function Calling selected `{tool_name}`.",
                confidence=0.9,
            )
        except Exception:
            return None

    def _parse(self, schema: type[BaseModel], system_prompt: str, message: str, memory: list[dict], rag_context: dict | None = None):
        memory_text = "\n".join(
            f"- {item.get('user_message')}: intent={item.get('intent')}, tool={item.get('tool_name')}"
            for item in memory[-5:]
        )
        rag_text = format_rag_context(rag_context or {})
        try:
            completion = self._client.beta.chat.completions.parse(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "system", "content": f"Today is {today_jst().isoformat()}. Current month is {current_month()}."},
                    {"role": "system", "content": f"Recent memory:\n{memory_text or '(none)'}"},
                    {"role": "system", "content": f"Retrieved RAG context:\n{rag_text}"},
                    {"role": "user", "content": message},
                ],
                response_format=schema,
            )
            return completion.choices[0].message.parsed
        except Exception:
            return None


llm_client = LLMClient()


def _function_tools() -> list[dict]:
    names = {
        "add_transaction": "Record one concrete expense or income transaction.",
        "set_budget": "Set a monthly total or category budget.",
        "query_spending_summary": "Summarize spending, income, net, and category totals.",
        "compare_periods": "Compare current spending with the previous month.",
        "forecast_month_end": "Forecast month-end spending and budget risk.",
        "generate_spending_advice": "Generate savings or budget-control advice.",
        "top_transactions": "List the largest transactions for a period.",
    }
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string", "description": "Brief reason for selecting this function."}
                    },
                    "required": ["reason"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        }
        for name, description in names.items()
    ]


def _intent_for_tool(tool_name: str) -> str:
    return {
        "add_transaction": "ADD_TRANSACTION",
        "set_budget": "SET_BUDGET",
        "query_spending_summary": "QUERY_SUMMARY",
        "compare_periods": "COMPARE_PERIOD",
        "forecast_month_end": "FORECAST_SPENDING",
        "generate_spending_advice": "GENERATE_ADVICE",
        "top_transactions": "QUERY_TOP",
    }.get(tool_name, "UNKNOWN")
