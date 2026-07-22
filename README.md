# AI Expense Agent

> A transparent, tool-based personal finance agent for natural-language transaction recording, analytics, budgeting, forecasting, and spending advice.

自然言語による家計記録、支出分析、予算管理、月末予測、節約提案を、一つの対話インターフェースに統合した家計管理Agentです。

## Overview / 概要

AI Expense Agentは、自然言語メッセージから支出・収入やユーザーの意図を解析し、用途別の家計管理ツールを呼び分けるWebアプリケーションです。

```text
今日の昼食でラーメンに980円使った
今月の食費予算を30000円に設定して
今月はいくら使った？
先月より支出が増えた理由は？
月末に予算を超えそう？
節約方法を提案して
```

現在の実装は、挙動を追跡しやすい**ルールベースの意図分類・構造化パーサー**と、用途別に分離したツール群で構成されています。外部LLM APIなしでローカル実行でき、Agentが選択したツールと入出力をログに保存します。

## Key Features / 主な機能

- **自然言語による取引登録**
  - 金額、支出・収入、日付、カテゴリ、店舗名、メモを解析
- **Tool-based Agent Orchestration**
  - 意図に応じて取引、分析、予算、予測、助言ツールを選択
- **取引管理**
  - 登録、一覧、検索、更新、削除
- **支出分析**
  - 日・週・月単位の集計
  - カテゴリ別内訳
  - 日別トレンド
  - 前月同期比較
  - 高額支出の抽出
- **予算管理**
  - 月次総予算およびカテゴリ別予算
- **月末支出予測**
  - 現在までの支出ペースから月末支出を推定
  - 予算超過額とリスクレベルを表示
- **データに基づく節約提案・アラート**
- **CSVエクスポート**
- **Agent実行ログ**
  - 入力、判定意図、使用ツール、ツール入出力、成功状態を記録
- **Streamlit Dashboard**
  - チャット、取引管理、予算、分析結果を可視化

## Agent Architecture / アーキテクチャ

```text
User Message
     |
     v
Intent Classifier + Structured Parser
     |
     v
Agent Orchestrator
     |
     +--> Transaction Tool  ----> Add / Update / Delete / Search
     +--> Analytics Tool    ----> Summary / Trend / Comparison
     +--> Budget Tool       ----> Monthly / Category Budget
     +--> Forecast Tool     ----> Month-end Spending Forecast
     +--> Advice Tool       ----> Suggestions / Alerts
     |
     v
SQLite Database + Agent Logs
     |
     v
FastAPI Response / Streamlit UI
```

Agentロジック、データアクセス、分析処理を分離しているため、将来的に分類・抽出部分をLLMのStructured OutputsやFunction Callingへ置き換えられる構成です。

## Tech Stack / 技術スタック

| Layer | Technology |
|---|---|
| Backend API | FastAPI |
| ORM / Database | SQLAlchemy, SQLite |
| Frontend | Streamlit |
| Validation | Pydantic |
| Data Processing | pandas |
| Testing | pytest |
| Language | Python |

## Project Structure / ディレクトリ構成

```text
AI_expense_agent/
├── backend/
│   ├── app/
│   │   ├── agents/          # Intent classification and orchestration
│   │   ├── api/             # FastAPI routes
│   │   ├── core/            # Configuration and database
│   │   ├── models/          # SQLAlchemy models
│   │   ├── repositories/    # Data-access layer
│   │   ├── services/        # Date and category utilities
│   │   ├── tools/           # Transaction, analytics, budget, forecast, advice
│   │   └── main.py          # FastAPI entry point
│   ├── requirements.txt
│   └── tests/
├── frontend/
│   ├── app.py               # Streamlit application
│   └── requirements.txt
└── README.md
```

## Quick Start / 実行方法

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/IshouKo/AI_expense_agent.git
cd AI_expense_agent
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r backend/requirements.txt -r frontend/requirements.txt
```

### 3. Start the FastAPI backend

```bash
cd backend
uvicorn app.main:app --reload
```

- Health check: `http://127.0.0.1:8000/health`
- Swagger UI: `http://127.0.0.1:8000/docs`

### 4. Start the Streamlit frontend

Open another terminal from the repository root:

```bash
source .venv/bin/activate
cd frontend
streamlit run app.py
```

## API Example / API使用例

```bash
curl -X POST http://127.0.0.1:8000/api/v1/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"今日の昼食でラーメンに980円使った"}'
```

## Main API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/agent/chat` | Natural-language agent interface |
| GET / POST | `/api/v1/transactions` | List or create transactions |
| PATCH / DELETE | `/api/v1/transactions/{id}` | Update or delete a transaction |
| GET | `/api/v1/analytics/summary` | Income and expense summary |
| GET | `/api/v1/analytics/categories` | Category breakdown |
| GET | `/api/v1/analytics/trend` | Daily spending trend |
| GET | `/api/v1/analytics/compare` | Period comparison |
| GET | `/api/v1/budgets/{month}` | Read monthly budgets |
| POST | `/api/v1/budgets` | Create or update a budget |
| GET | `/api/v1/forecast/{month}` | Month-end spending forecast |
| POST | `/api/v1/advice/generate` | Generate spending advice |
| GET | `/api/v1/alerts` | Budget and spending alerts |
| GET | `/api/v1/export/csv` | Export transactions as CSV |

## Testing / テスト

```bash
cd backend
pytest
```

## Current Scope / 現在の位置付け

本リポジトリは、Agent設計と家計データ分析を検証するための**シングルユーザー向けプロトタイプ**です。

現在の意図分類と情報抽出は主にルールベースです。そのため、挙動が説明可能で低コストに動作する一方、自由な言い回し、曖昧な入力、複雑な複合命令への対応には制限があります。

## Roadmap / 今後の拡張

- LLM Structured Outputsによる取引情報抽出
- Function Callingを用いた動的ツール選択
- 会話履歴とユーザー設定を保持する長期メモリ
- 複合命令の分解とマルチステップ実行
- 異常支出検知と時系列予測モデル
- 分類・予測精度の定量評価
- ユーザー認証とマルチユーザー対応
- PostgreSQLおよびクラウド環境への移行
- Docker化とCI/CD
