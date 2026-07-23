import json

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AgentLog


def load_recent_memory(db: Session, user_id: int) -> list[dict]:
    limit = get_settings().agent_memory_limit
    rows = (
        db.query(AgentLog)
        .filter(AgentLog.user_id == user_id)
        .order_by(AgentLog.created_at.desc(), AgentLog.id.desc())
        .limit(limit)
        .all()
    )
    memory = []
    for row in reversed(rows):
        memory.append(
            {
                "user_message": row.user_message,
                "intent": row.detected_intent,
                "tool_name": row.tool_name,
                "success": row.success,
                "tool_output": _loads(row.tool_output),
            }
        )
    return memory


def memory_summary(memory: list[dict]) -> dict:
    last_success = next((item for item in reversed(memory) if item.get("success")), None)
    recent_intents = [item.get("intent") for item in memory if item.get("intent")]
    return {
        "turns_loaded": len(memory),
        "last_successful_intent": last_success.get("intent") if last_success else None,
        "recent_intents": recent_intents[-5:],
    }


def _loads(value: str | None):
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
