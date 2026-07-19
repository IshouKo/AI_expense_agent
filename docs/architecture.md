# AI Expense Agent Architecture

AI Expense Agent follows the V3 design rule: the database is the source of truth, and all financial calculations are deterministic backend code.

## Runtime

- FastAPI exposes transaction, analytics, budget, forecast, advice, export, and agent chat endpoints.
- SQLite stores users, transactions, budgets, saving goals, recurring transactions, and agent logs.
- The agent orchestrator classifies user intent, validates extracted parameters, calls a controlled tool, then formats a user-facing reply.
- Streamlit provides a lightweight portfolio-ready UI for dashboard, chat, transaction management, budgets, and insights.

## Current MVP Agent

The first implementation uses a rule-based parser so the project works without an LLM API key. It supports common Chinese expense phrases, relative dates, category keywords, income detection, and budget setting. The parser can later be replaced by OpenAI Structured Outputs while keeping the same tool layer.

## Deterministic Tools

- `transaction_tool.py`: create, list, update, and delete transactions.
- `analytics_tool.py`: period totals, category breakdowns, trends, top transactions, and month-over-month comparison.
- `budget_tool.py`: total and category budget upsert/read.
- `forecast_tool.py`: month-end spending forecast, budget overrun, confidence, and risk level.
- `advice_tool.py`: data-grounded suggestions based on forecast, budgets, and category changes.

## Safety Notes

- The agent does not execute SQL directly.
- All write operations go through Pydantic schemas and tool functions.
- Every chat request is written to `agent_logs`.
- CSV export is user-triggered.
