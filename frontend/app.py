import os
from datetime import date

import pandas as pd
import requests
import streamlit as st


API_BASE = os.getenv("EXPENSE_API_BASE", "http://127.0.0.1:8000/api/v1")


def api_get(path: str, **params):
    response = requests.get(f"{API_BASE}{path}", params={k: v for k, v in params.items() if v is not None}, timeout=10)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict | None = None, **params):
    response = requests.post(f"{API_BASE}{path}", json=payload, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


st.set_page_config(page_title="AI Expense Agent", page_icon="JPY", layout="wide")
st.title("AI Expense Agent")

tab_dashboard, tab_chat, tab_transactions, tab_budget, tab_insights = st.tabs(
    ["Dashboard", "Chat", "Transactions", "Budget", "Insights"]
)

month = date.today().strftime("%Y-%m")

with tab_dashboard:
    summary = api_get("/analytics/summary")
    forecast = api_get(f"/forecast/{month}")
    alerts = api_get("/alerts")["alerts"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("本月支出", f"{summary['total_expense']:,} JPY")
    c2.metric("本月收入", f"{summary['total_income']:,} JPY")
    c3.metric("预计月底", f"{forecast['predicted_month_end_spending']:,} JPY")
    c4.metric("风险", forecast["risk_level"])

    left, right = st.columns([2, 1])
    with left:
        category_df = pd.DataFrame(summary["by_category"])
        if not category_df.empty:
            st.bar_chart(category_df.set_index("category"))
        trend_df = pd.DataFrame(api_get("/analytics/trend"))
        if not trend_df.empty:
            st.line_chart(trend_df.set_index("date"))
    with right:
        st.subheader("Agent 提醒")
        for alert in alerts:
            st.info(alert)
        transactions = pd.DataFrame(api_get("/transactions"))
        st.subheader("最近交易")
        if not transactions.empty:
            st.dataframe(transactions[["transaction_date", "type", "amount", "category", "note"]].head(8), use_container_width=True)

with tab_chat:
    st.subheader("自然语言记账")
    with st.form("chat_form", clear_on_submit=True):
        message = st.text_input("输入", placeholder="今天午饭吃拉面花了980日元")
        submitted = st.form_submit_button("发送")
    if submitted and message:
        result = api_post("/agent/chat", {"message": message})
        st.success(result["message"])
        st.json(result["data"])

with tab_transactions:
    st.subheader("交易管理")
    with st.form("manual_transaction"):
        cols = st.columns(5)
        tx_type = cols[0].selectbox("类型", ["expense", "income"])
        amount = cols[1].number_input("金额", min_value=0, step=100)
        category = cols[2].text_input("类别", value="food")
        tx_date = cols[3].date_input("日期")
        fixed = cols[4].checkbox("固定支出")
        note = st.text_input("备注")
        if st.form_submit_button("新增交易"):
            api_post(
                "/transactions",
                {
                    "type": tx_type,
                    "amount": amount,
                    "currency": "JPY",
                    "category": category,
                    "note": note,
                    "transaction_date": tx_date.isoformat(),
                    "is_fixed": fixed,
                },
            )
            st.success("已新增交易")
    txs = pd.DataFrame(api_get("/transactions"))
    st.dataframe(txs, use_container_width=True)
    st.link_button("下载 CSV", f"{API_BASE}/export/csv")

with tab_budget:
    st.subheader("预算管理")
    with st.form("budget_form"):
        cols = st.columns(3)
        budget_month = cols[0].text_input("月份", value=month)
        budget_category = cols[1].text_input("类别（留空为总预算）")
        budget_amount = cols[2].number_input("预算金额", min_value=0, step=1000)
        if st.form_submit_button("保存预算"):
            api_post("/budgets", {"month": budget_month, "category": budget_category or None, "amount": budget_amount})
            st.success("预算已保存")
    st.dataframe(pd.DataFrame(api_get(f"/budgets/{month}")), use_container_width=True)

with tab_insights:
    st.subheader("分析与建议")
    comparison = api_get("/analytics/compare")
    advice = api_post("/advice/generate", None, month=month)
    st.metric("本月同期差额", f"{comparison['difference']:,} JPY")
    st.write(advice["message"])
    st.json(advice["forecast"])
