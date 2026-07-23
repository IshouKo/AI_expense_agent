import re
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AgentLog, Transaction
from app.services.categories import CATEGORIES, KEYWORD_RULES


TOKEN_RE = re.compile(r"[a-z0-9]+|[一-龥ぁ-んァ-ンー]+", re.IGNORECASE)


def retrieve_context(db: Session, user_id: int, query: str) -> dict[str, Any]:
    documents = _transaction_documents(db, user_id) + _agent_log_documents(db, user_id) + _knowledge_documents()
    scored = []
    query_terms = _terms(query)
    for document in documents:
        score = _score(query, query_terms, document["text"])
        if score > 0:
            scored.append({**document, "score": round(score, 4)})
    scored.sort(key=lambda item: (item["score"], item.get("date") or ""), reverse=True)
    top_k = get_settings().rag_top_k
    return {
        "mode": "local_keyword_rag",
        "query": query,
        "top_k": top_k,
        "documents": scored[:top_k],
        "total_candidates": len(documents),
    }


def rag_summary(context: dict[str, Any]) -> dict[str, Any]:
    documents = context.get("documents", [])
    return {
        "mode": context.get("mode"),
        "documents_retrieved": len(documents),
        "sources": [item.get("source") for item in documents],
    }


def format_rag_context(context: dict[str, Any]) -> str:
    documents = context.get("documents", [])
    if not documents:
        return "(no retrieved context)"
    lines = []
    for item in documents:
        lines.append(f"- [{item['source']}:{item['id']}] score={item['score']} {item['text']}")
    return "\n".join(lines)


def _transaction_documents(db: Session, user_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .limit(200)
        .all()
    )
    docs = []
    for row in rows:
        text = " ".join(
            str(part)
            for part in [
                row.type,
                row.amount,
                row.currency,
                row.category,
                row.merchant,
                row.note,
                row.transaction_date.isoformat(),
            ]
            if part is not None
        )
        docs.append(
            {
                "source": "transaction",
                "id": row.id,
                "date": row.transaction_date.isoformat(),
                "text": text,
                "metadata": {
                    "amount": row.amount,
                    "category": row.category,
                    "merchant": row.merchant,
                    "transaction_date": row.transaction_date.isoformat(),
                },
            }
        )
    return docs


def _agent_log_documents(db: Session, user_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(AgentLog)
        .filter(AgentLog.user_id == user_id)
        .order_by(AgentLog.created_at.desc(), AgentLog.id.desc())
        .limit(100)
        .all()
    )
    docs = []
    for row in rows:
        text = " ".join(part for part in [row.user_message, row.detected_intent, row.tool_name, row.tool_output] if part)
        docs.append(
            {
                "source": "agent_log",
                "id": row.id,
                "date": _safe_date(row.created_at),
                "text": text,
                "metadata": {"intent": row.detected_intent, "tool_name": row.tool_name, "success": row.success},
            }
        )
    return docs


def _knowledge_documents() -> list[dict[str, Any]]:
    docs = []
    for category, label in CATEGORIES.items():
        keywords = ", ".join(KEYWORD_RULES.get(category, []))
        docs.append(
            {
                "source": "category_knowledge",
                "id": category,
                "date": "",
                "text": f"category={category} label={label} keywords={keywords}",
                "metadata": {"category": category, "label": label},
            }
        )
    docs.extend(
        [
            {
                "source": "tool_knowledge",
                "id": "summary",
                "date": "",
                "text": "Use query_spending_summary for questions about totals, income, expenses, net amount, categories, today, this week, this month, or recent 30 days.",
                "metadata": {"tool": "query_spending_summary"},
            },
            {
                "source": "tool_knowledge",
                "id": "forecast",
                "date": "",
                "text": "Use forecast_month_end for month-end predictions, over-budget risk, and whether spending may exceed budget.",
                "metadata": {"tool": "forecast_month_end"},
            },
        ]
    )
    return docs


def _score(query: str, query_terms: set[str], text: str) -> float:
    text_lower = text.lower()
    text_terms = _terms(text)
    overlap = len(query_terms & text_terms)
    substring_hits = sum(1 for term in query_terms if len(term) >= 2 and term in text_lower)
    number_hits = sum(1 for number in re.findall(r"\d+", query) if number and number in text_lower)
    return overlap + substring_hits * 0.7 + number_hits * 1.5


def _terms(text: str) -> set[str]:
    lowered = text.lower()
    terms = set(TOKEN_RE.findall(lowered))
    for token in list(terms):
        if _contains_cjk(token) and len(token) > 2:
            terms.update(token[index : index + 2] for index in range(len(token) - 1))
    return {term for term in terms if term.strip()}


def _contains_cjk(text: str) -> bool:
    return any("\u3040" <= char <= "\u30ff" or "\u4e00" <= char <= "\u9fff" for char in text)


def _safe_date(value) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value or "")
