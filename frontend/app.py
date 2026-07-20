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


st.set_page_config(page_title="AI家計管理エージェント", page_icon="JPY", layout="wide")
st.title("AI家計管理エージェント")

tab_dashboard, tab_chat, tab_transactions, tab_budget, tab_insights = st.tabs(
    ["ダッシュボード", "チャット", "取引", "予算", "分析"]
)

month = date.today().strftime("%Y-%m")

with tab_dashboard:
    summary = api_get("/analytics/summary")
    forecast = api_get(f"/forecast/{month}")
    alerts = api_get("/alerts")["alerts"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("今月の支出", f"{summary['total_expense']:,} JPY")
    c2.metric("今月の収入", f"{summary['total_income']:,} JPY")
    c3.metric("月末予測", f"{forecast['predicted_month_end_spending']:,} JPY")
    risk_labels = {"low": "低", "medium": "中", "high": "高", "critical": "深刻"}
    c4.metric("リスク", risk_labels.get(forecast["risk_level"], forecast["risk_level"]))

    left, right = st.columns([2, 1])
    with left:
        category_df = pd.DataFrame(summary["by_category"])
        if not category_df.empty:
            st.bar_chart(category_df.set_index("category"))
        trend_df = pd.DataFrame(api_get("/analytics/trend"))
        if not trend_df.empty:
            st.line_chart(trend_df.set_index("date"))
    with right:
        st.subheader("エージェント通知")
        for alert in alerts:
            st.info(alert)
        transactions = pd.DataFrame(api_get("/transactions"))
        st.subheader("最近の取引")
        if not transactions.empty:
            recent = transactions[["transaction_date", "type", "amount", "category", "note"]].head(8).copy()
            recent["type"] = recent["type"].map({"expense": "支出", "income": "収入"}).fillna(recent["type"])
            recent = recent.rename(
                columns={
                    "transaction_date": "日付",
                    "type": "種別",
                    "amount": "金額",
                    "category": "カテゴリ",
                    "note": "メモ",
                }
            )
            st.dataframe(recent, use_container_width=True)

with tab_chat:
    st.subheader("自然言語で記録")
    with st.form("chat_form", clear_on_submit=True):
        message = st.text_input("入力", placeholder="今日の昼食でラーメンに980円使った")
        submitted = st.form_submit_button("送信")
    if submitted and message:
        result = api_post("/agent/chat", {"message": message})
        st.success(result["message"])
        st.json(result["data"])

with tab_transactions:
    st.subheader("取引管理")
    with st.form("manual_transaction"):
        cols = st.columns(5)
        tx_type = cols[0].selectbox("種別", ["expense", "income"], format_func=lambda value: {"expense": "支出", "income": "収入"}[value])
        amount = cols[1].number_input("金額", min_value=0, step=100)
        category = cols[2].text_input("カテゴリ", value="food")
        tx_date = cols[3].date_input("日付")
        fixed = cols[4].checkbox("固定支出")
        note = st.text_input("メモ")
        if st.form_submit_button("取引を追加"):
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
            st.success("取引を追加しました")
    txs = pd.DataFrame(api_get("/transactions"))
    if not txs.empty:
        display_txs = txs.copy()
        if "type" in display_txs:
            display_txs["type"] = display_txs["type"].map({"expense": "支出", "income": "収入"}).fillna(display_txs["type"])
        display_txs = display_txs.rename(
            columns={
                "id": "ID",
                "transaction_date": "日付",
                "type": "種別",
                "amount": "金額",
                "currency": "通貨",
                "category": "カテゴリ",
                "merchant": "店舗",
                "note": "メモ",
                "source": "登録元",
                "is_fixed": "固定",
                "confidence": "信頼度",
                "created_at": "作成日時",
                "updated_at": "更新日時",
            }
        )
        st.dataframe(display_txs, use_container_width=True)
    else:
        st.info("取引データはまだありません。")
    st.link_button("CSVをダウンロード", f"{API_BASE}/export/csv")

with tab_budget:
    st.subheader("予算管理")
    with st.form("budget_form"):
        cols = st.columns(3)
        budget_month = cols[0].text_input("月", value=month)
        budget_category = cols[1].text_input("カテゴリ（空欄なら総予算）")
        budget_amount = cols[2].number_input("予算額", min_value=0, step=1000)
        if st.form_submit_button("予算を保存"):
            api_post("/budgets", {"month": budget_month, "category": budget_category or None, "amount": budget_amount})
            st.success("予算を保存しました")
    budgets = pd.DataFrame(api_get(f"/budgets/{month}"))
    if not budgets.empty:
        budgets = budgets.rename(columns={"month": "月", "category": "カテゴリ", "amount": "金額"})
    st.dataframe(budgets, use_container_width=True)

with tab_insights:
    st.subheader("分析と提案")
    comparison = api_get("/analytics/compare")
    advice = api_post("/advice/generate", None, month=month)
    st.metric("前月同期との差額", f"{comparison['difference']:,} JPY")
    st.write(advice["message"])
    st.json(advice["forecast"])
