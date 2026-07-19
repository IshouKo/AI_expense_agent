import json

from sqlalchemy.orm import Session

from app.agents.parser import parse_budget, parse_transaction
from app.models import AgentLog
from app.repositories.user_repository import get_or_create_default_user
from app.services.categories import display_category
from datetime import timedelta

from app.services.date_utils import current_month, month_bounds, previous_month_same_span, today_jst, week_bounds
from app.tools.advice_tool import generate_spending_advice
from app.tools.analytics_tool import compare_periods, query_spending_summary, top_transactions
from app.tools.budget_tool import set_budget
from app.tools.forecast_tool import forecast_month_end
from app.tools.transaction_tool import add_transaction


def handle_chat(db: Session, message: str) -> dict:
    user = get_or_create_default_user(db)
    intent = classify_intent(message)
    tool_name = None
    tool_input = None
    tool_output = None
    success = True

    try:
        if intent == "SET_BUDGET":
            payload = parse_budget(message)
            if not payload:
                return _reply(db, user.id, message, intent, None, None, {"error": "missing_amount"}, False, "预算金额没有识别出来，请再输入一次。", {})
            budget = set_budget(db, user.id, payload)
            tool_name = "set_budget"
            tool_input = payload.model_dump()
            data = {"budget_id": budget.id, "month": budget.month, "category": budget.category, "amount": budget.amount}
            label = "总预算" if budget.category is None else f"{display_category(budget.category)}预算"
            response = f"已设置 {budget.month} 的{label}为 {budget.amount:,} 日元。"
        elif intent == "QUERY_SUMMARY":
            start, end = _period_from_message(message)
            data = query_spending_summary(db, user.id, start, end)
            tool_name = "query_spending_summary"
            tool_input = {"start_date": str(start), "end_date": str(end)}
            response = _format_summary(data)
        elif intent == "COMPARE_PERIOD":
            start, end = month_bounds(current_month())
            effective_end = min(end, today_jst())
            previous_start, previous_end = previous_month_same_span(start, effective_end)
            data = compare_periods(db, user.id, start, effective_end, previous_start, previous_end)
            tool_name = "compare_periods"
            tool_input = {"current_start": str(start), "current_end": str(effective_end)}
            response = _format_comparison(data)
        elif intent == "FORECAST_SPENDING":
            data = forecast_month_end(db, user.id, current_month())
            tool_name = "forecast_month_end"
            tool_input = {"month": current_month()}
            response = _format_forecast(data)
        elif intent == "GENERATE_ADVICE":
            data = generate_spending_advice(db, user.id, current_month())
            tool_name = "generate_spending_advice"
            tool_input = {"month": current_month()}
            response = data["message"]
        elif intent == "QUERY_TOP":
            start, end = _period_from_message(message)
            txs = top_transactions(db, user.id, start, end, 3)
            data = {"transactions": [{"id": t.id, "amount": t.amount, "category": t.category, "note": t.note} for t in txs]}
            tool_name = "top_transactions"
            tool_input = {"start_date": str(start), "end_date": str(end)}
            response = "本期最大的三笔支出：\n" + "\n".join(
                f"- {t.amount:,} 日元 / {display_category(t.category)} / {t.note or t.merchant or '无备注'}" for t in txs
            )
        else:
            payload = parse_transaction(message)
            if not payload:
                return _reply(db, user.id, message, "UNKNOWN", None, None, {"error": "unsupported"}, False, "我还没有识别出金额或明确意图。可以试试：今天午饭980日元。", {})
            tx = add_transaction(db, user.id, payload)
            intent = "ADD_TRANSACTION"
            tool_name = "add_transaction"
            tool_input = payload.model_dump(mode="json")
            data = {"transaction_id": tx.id, "amount": tx.amount, "category": tx.category, "confidence": tx.confidence}
            response = f"已记录：{tx.amount:,} 日元，类别为{display_category(tx.category)}，日期 {tx.transaction_date.isoformat()}。"
        return _reply(db, user.id, message, intent, tool_name, tool_input, data, success, response, data)
    except Exception as exc:
        tool_output = {"error": str(exc)}
        return _reply(db, user.id, message, intent, tool_name, tool_input, tool_output, False, "处理时出现错误，请稍后重试。", tool_output)


def classify_intent(message: str) -> str:
    if any(word in message for word in ["预算", "最多", "控制到"]) and any(char.isdigit() for char in message):
        return "SET_BUDGET"
    if any(word in message for word in ["建议", "怎么控制", "怎么省", "节省"]):
        return "GENERATE_ADVICE"
    if any(word in message for word in ["超预算", "月底", "预测", "会超"]):
        return "FORECAST_SPENDING"
    if any(word in message for word in ["为什么", "比上个月", "上涨", "增长"]):
        return "COMPARE_PERIOD"
    if any(word in message for word in ["最大", "前三", "三笔"]):
        return "QUERY_TOP"
    if any(word in message for word in ["花了多少", "收入", "支出", "统计", "多少钱"]):
        return "QUERY_SUMMARY"
    return "ADD_TRANSACTION"


def _period_from_message(message: str):
    if "今天" in message:
        day = today_jst()
        return day, day
    if "本周" in message or "这周" in message:
        return week_bounds()
    if "最近30天" in message:
        end = today_jst()
        return end - timedelta(days=29), end
    return month_bounds(current_month())


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


def _reply(db: Session, user_id: int, message: str, intent: str, tool_name: str | None, tool_input, tool_output, success: bool, response: str, data: dict) -> dict:
    db.add(
        AgentLog(
            user_id=user_id,
            user_message=message,
            detected_intent=intent,
            tool_name=tool_name,
            tool_input=json.dumps(tool_input, ensure_ascii=False, default=str) if tool_input is not None else None,
            tool_output=json.dumps(tool_output, ensure_ascii=False, default=str) if tool_output is not None else None,
            success=success,
        )
    )
    db.commit()
    return {"intent": intent, "message": response, "data": data}
