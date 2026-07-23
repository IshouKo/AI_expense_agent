import json
from typing import Any, TypedDict

from sqlalchemy.orm import Session

from app.agents.llm_client import llm_client
from app.agents.memory import load_recent_memory, memory_summary
from app.agents.rag import rag_summary, retrieve_context
from app.agents.tool_registry import TOOL_DESCRIPTIONS, execute_tool
from app.models import AgentLog
from app.repositories.user_repository import get_or_create_default_user
from app.services.categories import display_category


class AgentState(TypedDict, total=False):
    db: Session
    user_id: int
    message: str
    memory: list[dict]
    memory_summary: dict
    rag_context: dict
    rag_summary: dict
    plan: list[dict]
    reasoning: str
    intent: str
    tool_name: str | None
    tool_input: Any
    tool_output: Any
    success: bool
    response: str
    data: dict
    extracted_transaction: Any


def handle_chat(db: Session, message: str) -> dict:
    user = get_or_create_default_user(db)
    state: AgentState = {"db": db, "user_id": user.id, "message": message}
    result = _build_graph().invoke(state)
    _log_turn(db, result)
    return {
        "intent": result["intent"],
        "message": result["response"],
        "data": {
            **(result.get("data") or {}),
            "agent": {
                "plan": result.get("plan", []),
                "reasoning": result.get("reasoning"),
                "memory": result.get("memory_summary", {}),
                "rag": result.get("rag_summary", {}),
                "tool": result.get("tool_name"),
            },
        },
    }


def _build_graph():
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(AgentState)
        graph.add_node("load_memory", _load_memory)
        graph.add_node("retrieve_context", _retrieve_context)
        graph.add_node("plan", _plan)
        graph.add_node("select_tool", _select_tool)
        graph.add_node("execute_tool", _execute_tool)
        graph.add_node("respond", _respond)
        graph.set_entry_point("load_memory")
        graph.add_edge("load_memory", "retrieve_context")
        graph.add_edge("retrieve_context", "plan")
        graph.add_edge("plan", "select_tool")
        graph.add_edge("select_tool", "execute_tool")
        graph.add_edge("execute_tool", "respond")
        graph.add_edge("respond", END)
        return graph.compile()
    except Exception:
        return _FallbackGraph([_load_memory, _retrieve_context, _plan, _select_tool, _execute_tool, _respond])


class _FallbackGraph:
    def __init__(self, nodes):
        self.nodes = nodes

    def invoke(self, state: AgentState) -> AgentState:
        for node in self.nodes:
            state.update(node(state))
        return state


def _load_memory(state: AgentState) -> AgentState:
    memory = load_recent_memory(state["db"], state["user_id"])
    return {"memory": memory, "memory_summary": memory_summary(memory)}


def _retrieve_context(state: AgentState) -> AgentState:
    context = retrieve_context(state["db"], state["user_id"], state["message"])
    return {"rag_context": context, "rag_summary": rag_summary(context)}


def _plan(state: AgentState) -> AgentState:
    message = state["message"]
    extracted = llm_client.extract_transaction(message, state.get("memory", []), state.get("rag_context"))
    likely_intent = classify_intent(message)
    plan = [
        {"step": "Load recent AgentLog entries as conversation memory.", "status": "done"},
        {"step": "Retrieve relevant transactions, logs, and finance knowledge with local RAG.", "status": "done"},
        {"step": "Extract transaction details with OpenAI Structured Outputs when API key is configured.", "status": "done" if extracted else "fallback"},
        {"step": "Choose the best finance tool dynamically, then execute it.", "status": "pending"},
    ]
    rag_count = state.get("rag_summary", {}).get("documents_retrieved", 0)
    reasoning = (
        f"Retrieved {rag_count} RAG documents. Structured extraction is available."
        if extracted
        else f"Retrieved {rag_count} RAG documents. OpenAI key is empty or extraction was inconclusive; using deterministic parser fallback."
    )
    return {"plan": plan, "reasoning": reasoning, "intent": likely_intent, "extracted_transaction": extracted}


def _select_tool(state: AgentState) -> AgentState:
    decision = llm_client.decide_tool(state["message"], state.get("memory", []), state.get("rag_context"))
    if decision:
        return {
            "intent": decision.intent,
            "tool_name": None if decision.tool_name == "none" else decision.tool_name,
            "reasoning": f"{state.get('reasoning')} Tool decision: {decision.reasoning_summary}",
            "plan": _mark_plan(state.get("plan", []), "Choose the best finance tool dynamically, then execute it.", "done"),
        }
    intent = state.get("intent") or classify_intent(state["message"])
    tool_name = _tool_for_intent(intent)
    return {
        "intent": intent,
        "tool_name": tool_name,
        "reasoning": f"{state.get('reasoning')} Rule-based tool selection chose {tool_name or 'none'}.",
        "plan": _mark_plan(state.get("plan", []), "Choose the best finance tool dynamically, then execute it.", "done"),
    }


def _execute_tool(state: AgentState) -> AgentState:
    tool_name = state.get("tool_name")
    if not tool_name:
        return {"success": False, "tool_input": None, "tool_output": {"error": "unsupported"}, "data": {}}
    result = execute_tool(state["db"], state["user_id"], tool_name, state["message"], state.get("extracted_transaction"))
    return {
        "success": result["ok"],
        "tool_input": result.get("tool_input"),
        "tool_output": result.get("data") if result["ok"] else {"error": result.get("error")},
        "data": result.get("data") or {},
    }


def _respond(state: AgentState) -> AgentState:
    if not state.get("success"):
        error = (state.get("tool_output") or {}).get("error")
        if error == "missing_amount":
            response = "预算金额没有识别出来，请再输入一次。"
        else:
            response = "我还没有识别出金额或明确意图。可以试试：今天午饭980日元。"
        return {"response": response}
    data = state.get("data") or {}
    tool_name = state.get("tool_name")
    if tool_name == "set_budget":
        label = "总预算" if data.get("category") is None else f"{display_category(data['category'])}预算"
        response = f"已设置 {data['month']} 的{label}为 {data['amount']:,} 日元。"
    elif tool_name == "query_spending_summary":
        response = _format_summary(data)
    elif tool_name == "compare_periods":
        response = _format_comparison(data)
    elif tool_name == "forecast_month_end":
        response = _format_forecast(data)
    elif tool_name == "generate_spending_advice":
        response = data["message"]
    elif tool_name == "top_transactions":
        txs = data.get("transactions", [])
        response = "本期最大的三笔支出：\n" + "\n".join(
            f"- {t['amount']:,} 日元 / {display_category(t['category'])} / {t.get('note') or t.get('merchant') or '无备注'}" for t in txs
        )
    else:
        response = f"已记录：{data['amount']:,} 日元，类别为{display_category(data['category'])}。"
    return {"response": response}


def classify_intent(message: str) -> str:
    if any(word in message for word in ["预算", "予算", "最多", "控制到"]) and any(char.isdigit() for char in message):
        return "SET_BUDGET"
    if any(word in message for word in ["建议", "アドバイス", "怎么控制", "怎么省", "節約", "节省"]):
        return "GENERATE_ADVICE"
    if any(word in message for word in ["超预算", "予算超過", "月底", "月末", "预测", "予測", "会超"]):
        return "FORECAST_SPENDING"
    if any(word in message for word in ["为什么", "比上个月", "先月", "上涨", "増え", "增长"]):
        return "COMPARE_PERIOD"
    if any(word in message for word in ["最大", "前三", "三筆", "三笔"]):
        return "QUERY_TOP"
    if any(word in message for word in ["花了多少", "いくら", "收入", "収入", "支出", "统计", "集計", "多少钱"]):
        return "QUERY_SUMMARY"
    return "ADD_TRANSACTION"


def _tool_for_intent(intent: str) -> str | None:
    return {
        "ADD_TRANSACTION": "add_transaction",
        "SET_BUDGET": "set_budget",
        "QUERY_SUMMARY": "query_spending_summary",
        "COMPARE_PERIOD": "compare_periods",
        "FORECAST_SPENDING": "forecast_month_end",
        "GENERATE_ADVICE": "generate_spending_advice",
        "QUERY_TOP": "top_transactions",
    }.get(intent)


def _mark_plan(plan: list[dict], step: str, status: str) -> list[dict]:
    return [{**item, "status": status} if item.get("step") == step else item for item in plan]


def _format_summary(data: dict) -> str:
    lines = [f"本期支出 {data['total_expense']:,} 日元，收入 {data['total_income']:,} 日元，净额 {data['net']:,} 日元。"]
    if data["by_category"]:
        lines.append("主要类别：")
        lines.extend(f"- {display_category(item['category'])}: {item['amount']:,} 日元" for item in data["by_category"][:5])
    return "\n".join(lines)


def _format_comparison(data: dict) -> str:
    diff = data["difference"]
    direction = "多" if diff >= 0 else "少"
    lines = [f"本月同期比上月同期{direction}支出 {abs(diff):,} 日元。"]
    growth = [item for item in data["category_changes"] if item["difference"] > 0][:3]
    if growth:
        lines.append("主要增加来自：")
        lines.extend(f"- {display_category(item['category'])}: +{item['difference']:,} 日元" for item in growth)
    return "\n".join(lines)


def _format_forecast(data: dict) -> str:
    if data["monthly_budget"] is None:
        return f"预计月底支出约 {data['predicted_month_end_spending']:,} 日元。还没有设置月度总预算，所以暂时无法判断是否超预算。"
    over = data["predicted_over_budget"] or 0
    if over > 0:
        return f"预计月底支出约 {data['predicted_month_end_spending']:,} 日元，预算 {data['monthly_budget']:,} 日元，可能超出 {over:,} 日元。风险等级：{data['risk_level']}。"
    return f"预计月底支出约 {data['predicted_month_end_spending']:,} 日元，低于预算 {data['monthly_budget']:,} 日元。风险等级：{data['risk_level']}。"


def _log_turn(db: Session, state: AgentState) -> None:
    db.add(
        AgentLog(
            user_id=state["user_id"],
            user_message=state["message"],
            detected_intent=state.get("intent"),
            tool_name=state.get("tool_name"),
            tool_input=json.dumps(state.get("tool_input"), ensure_ascii=False, default=str) if state.get("tool_input") is not None else None,
            tool_output=json.dumps(
                {
                    "result": state.get("tool_output"),
                    "plan": state.get("plan", []),
                    "reasoning": state.get("reasoning"),
                    "memory": state.get("memory_summary", {}),
                    "rag": state.get("rag_summary", {}),
                    "available_tools": TOOL_DESCRIPTIONS,
                },
                ensure_ascii=False,
                default=str,
            ),
            success=bool(state.get("success")),
        )
    )
    db.commit()
