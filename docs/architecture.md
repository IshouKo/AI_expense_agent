# AI Expense Agent Architecture

AI Expense Agent follows the V3 design rule: the database is the source of truth, and all financial calculations are deterministic backend code.

## Runtime

- FastAPI exposes transaction, analytics, budget, forecast, advice, export, and agent chat endpoints.
- SQLite stores users, transactions, budgets, saving goals, recurring transactions, and agent logs.
- The agent orchestrator is a LangGraph workflow that loads memory, retrieves RAG context, plans, selects a tool, executes deterministic backend code, then formats a user-facing reply.
- Local RAG searches recent transactions, agent logs, category knowledge, and tool knowledge without requiring an external vector database.
- OpenAI Structured Outputs can extract transaction fields into Pydantic schemas when `EXPENSE_OPENAI_API_KEY` is configured.
- Function Calling tool decisions choose between transaction, analytics, budget, forecast, advice, and top-transaction tools. If the API key is empty, the orchestrator uses deterministic fallback routing.
- Streamlit provides a lightweight portfolio-ready UI for dashboard, chat, transaction management, budgets, and insights.

## Current Agent

The agent keeps the tool layer deterministic and lets the LLM handle language understanding only when configured.

```text
User message
  -> load_memory
  -> retrieve_context
  -> plan
  -> select_tool
  -> execute_tool
  -> respond
```

The `retrieve_context` node performs local keyword RAG over SQLite records and built-in finance knowledge. The `plan` node attempts Structured Outputs extraction for transactions using the retrieved context. The `select_tool` node asks the model for a function call using the same context. Both nodes fall back to the local parser/classifier when the OpenAI API key is blank or the model call fails.

Memory management reuses `agent_logs`: recent successful and failed turns are loaded into each graph run, summarized, passed to the LLM prompt, and returned in `data.agent.memory`.

## Deterministic Tools

- `transaction_tool.py`: create, list, update, and delete transactions.
- `analytics_tool.py`: period totals, category breakdowns, trends, top transactions, and month-over-month comparison.
- `budget_tool.py`: total and category budget upsert/read.
- `forecast_tool.py`: month-end spending forecast, budget overrun, confidence, and risk level.
- `advice_tool.py`: data-grounded suggestions based on forecast, budgets, and category changes.

## Agent Response Metadata

`POST /api/v1/agent/chat` returns normal user-facing data plus an `agent` metadata block:

```json
{
  "intent": "ADD_TRANSACTION",
  "message": "已记录：980 日元，类别为餐饮。",
  "data": {
    "transaction_id": 1,
    "amount": 980,
    "category": "food",
    "agent": {
      "plan": [],
      "reasoning": "...",
      "memory": {"turns_loaded": 3},
      "rag": {"mode": "local_keyword_rag", "documents_retrieved": 2},
      "tool": "add_transaction"
    }
  }
}
```

## Safety Notes

- The agent does not execute SQL directly.
- All write operations go through Pydantic schemas and tool functions.
- Every chat request is written to `agent_logs`.
- LLM output never writes directly to the database; it must pass Pydantic validation and controlled tool functions.
- CSV export is user-triggered.
