from sqlalchemy.orm import Session

from app.services.categories import display_category
from app.services.date_utils import month_bounds, previous_month_same_span, today_jst
from app.tools.analytics_tool import compare_periods, query_spending_summary
from app.tools.budget_tool import get_budgets
from app.tools.forecast_tool import forecast_month_end


def generate_spending_advice(db: Session, user_id: int, month: str) -> dict:
    start, end = month_bounds(month)
    current_end = min(end, today_jst()) if today_jst() >= start else end
    previous_start, previous_end = previous_month_same_span(start, current_end)
    forecast = forecast_month_end(db, user_id, month)
    comparison = compare_periods(db, user_id, start, current_end, previous_start, previous_end)
    budgets = get_budgets(db, user_id, month)
    category_budgets = {budget.category: budget.amount for budget in budgets if budget.category}
    summary = query_spending_summary(db, user_id, start, end)
    spent_by_category = {item["category"]: item["amount"] for item in summary["by_category"]}

    suggestions = []
    if forecast["monthly_budget"] and forecast["predicted_over_budget"] and forecast["predicted_over_budget"] > 0:
        remaining_budget = max(forecast["monthly_budget"] - forecast["current_spending"], 0)
        daily = round(remaining_budget / max(forecast["remaining_days"], 1))
        suggestions.append(f"按照当前速度，月底可能超预算约 {forecast['predicted_over_budget']:,} 日元；剩余每日可用预算约 {daily:,} 日元。")
    else:
        suggestions.append("按照当前速度，月度预算风险不高，可以继续保持当前记录频率。")

    for change in comparison["category_changes"][:3]:
        if change["difference"] > 0:
            suggestions.append(
                f"{display_category(change['category'])} 比上期多 {change['difference']:,} 日元，优先检查这一类是否有一次性或非必要支出。"
            )

    for category, budget in category_budgets.items():
        spent = spent_by_category.get(category, 0)
        if budget and spent / budget >= 0.8:
            suggestions.append(f"{display_category(category)}预算已使用 {spent / budget:.0%}，本月剩余支出建议更谨慎。")

    return {
        "month": month,
        "forecast": forecast,
        "comparison": comparison,
        "suggestions": suggestions[:5],
        "message": "\n".join(f"- {item}" for item in suggestions[:5]),
    }
