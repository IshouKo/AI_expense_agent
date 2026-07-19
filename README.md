# AI Expense Agent

FastAPI + SQLite + Streamlit implementation based on `ai_expense_agent_readme.md`.

## Features

- Natural-language transaction entry in Chinese.
- Automatic rule-based category detection.
- Transaction CRUD.
- Day/week/month summaries.
- Category and daily trend analytics.
- Monthly and category budgets.
- Month-end spending forecast and risk level.
- Data-grounded advice and alerts.
- CSV export.

## Quick Start

```bash
cd /Users/Koishou/Desktop/ai_expense_agent
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt -r frontend/requirements.txt
```

Run the backend:

```bash
cd /Users/Koishou/Desktop/ai_expense_agent/backend
uvicorn app.main:app --reload
```

Run the frontend in another terminal:

```bash
cd /Users/Koishou/Desktop/ai_expense_agent/frontend
streamlit run app.py
```

Backend health check:

```bash
curl http://127.0.0.1:8000/health
```

Example chat request:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"今天午饭吃拉面花了980日元"}'
```

## API

- `POST /api/v1/agent/chat`
- `GET /api/v1/transactions`
- `POST /api/v1/transactions`
- `PATCH /api/v1/transactions/{id}`
- `DELETE /api/v1/transactions/{id}`
- `GET /api/v1/analytics/summary`
- `GET /api/v1/analytics/categories`
- `GET /api/v1/analytics/trend`
- `GET /api/v1/analytics/compare`
- `GET /api/v1/budgets/{month}`
- `POST /api/v1/budgets`
- `GET /api/v1/forecast/{month}`
- `POST /api/v1/advice/generate`
- `GET /api/v1/alerts`
- `GET /api/v1/export/csv`

## Tests

```bash
cd /Users/Koishou/Desktop/ai_expense_agent/backend
pytest
```
