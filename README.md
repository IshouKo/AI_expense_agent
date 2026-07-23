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

現在の実装は、**LangGraphベースのAgentワークフロー**、SQLite内の取引・会話ログ・カテゴリ知識を検索する**ローカルRAG**、OpenAI APIキー設定時の**Structured Outputsによる取引情報抽出**、**Function Callingによる動的ツール選択**、Planning & Reasoning、AgentLogを利用したMemory Managementで構成されています。OpenAI APIキーが空の場合は、既存のルールベース分類・パーサーへ自動フォールバックするため、外部LLM APIなしでもローカル実行できます。

## Key Features / 主な機能

- **自然言語による取引登録**
  - 金額、支出・収入、日付、カテゴリ、店舗名、メモを解析
- **LLM Structured Outputs**
  - `EXPENSE_OPENAI_API_KEY` 設定時、Pydanticスキーマに沿って取引情報を抽出
  - APIキー未設定時はルールベースの抽出にフォールバック
- **Function Calling Dynamic Tool Selection**
  - ユーザー意図に応じて取引、分析、予算、予測、助言ツールを動的に選択
- **LangGraph Orchestration**
  - Memory load、RAG retrieval、Planning、Tool selection、Tool execution、Response formattingをグラフとして実行
- **RAG**
  - 過去の取引、Agent実行ログ、カテゴリ/ツール知識を検索し、LLM抽出・ツール選択の参考コンテキストとして利用
  - 外部ベクターDBなしで動くローカルキーワード検索から開始
- **Planning & Reasoning**
  - 各チャット応答の `data.agent.plan` と `data.agent.reasoning` に実行計画と判断要約を付与
- **Memory Management**
  - `agent_logs` から直近の会話とツール実行結果を読み込み、次の判断に利用
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
LangGraph Agent
     |
     +--> Memory Node       ----> Recent AgentLog context
     +--> RAG Node          ----> Transactions / Logs / Knowledge retrieval
     +--> Planning Node     ----> Extraction plan + reasoning summary
     +--> Tool Select Node  ----> LLM decision / deterministic fallback
     +--> Tool Exec Node    ----> Controlled backend tools
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

Agentロジック、データアクセス、分析処理を分離し、LLMは理解・抽出・ツール選択に限定します。金額集計、予測、DB更新はバックエンドの決定的なツールで実行します。

## Tech Stack / 技術スタック

| Layer | Technology |
|---|---|
| Backend API | FastAPI |
| ORM / Database | SQLAlchemy, SQLite |
| Frontend | Streamlit |
| Validation | Pydantic |
| LLM Integration | OpenAI API Structured Outputs |
| Agent Workflow | LangGraph |
| Data Processing | pandas |
| Testing | pytest |
| Language | Python |

## Project Structure / ディレクトリ構成

```text
AI_expense_agent/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── orchestrator.py     # LangGraph workflow: memory -> RAG -> planning -> tool selection -> execution -> response
│   │   │   ├── llm_client.py       # OpenAI Structured Outputs and Function Calling integration with fallback behavior
│   │   │   ├── rag.py              # Local RAG over transactions, agent logs, category knowledge, and tool knowledge
│   │   │   ├── memory.py           # Loads recent AgentLog records as short-term conversation memory
│   │   │   ├── tool_registry.py    # Maps selected tool names to deterministic backend tool functions
│   │   │   ├── parser.py           # Rule-based amount/date/category extraction fallback
│   │   │   ├── prompts.py          # Prompt text location for future prompt templates
│   │   │   └── __init__.py
│   │   ├── api/
│   │   │   ├── routes.py           # FastAPI endpoints for agent chat, transactions, analytics, budgets, forecast, advice, export
│   │   │   └── __init__.py
│   │   ├── core/
│   │   │   ├── config.py           # Environment-based settings such as DB URL, OpenAI model/key, memory and RAG limits
│   │   │   ├── database.py         # SQLAlchemy engine, session factory, and Base model class
│   │   │   └── __init__.py
│   │   ├── models/
│   │   │   ├── models.py           # SQLAlchemy tables: users, transactions, budgets, goals, recurring transactions, agent logs
│   │   │   └── __init__.py
│   │   ├── repositories/
│   │   │   ├── user_repository.py  # Default-user lookup and creation helpers
│   │   │   └── __init__.py
│   │   ├── schemas/
│   │   │   ├── schemas.py          # Pydantic request/response schemas and validation rules
│   │   │   └── __init__.py
│   │   ├── services/
│   │   │   ├── categories.py       # Category labels, keyword rules, and display-name helpers
│   │   │   ├── date_utils.py       # JST date helpers, current month, week/month range calculations
│   │   │   └── __init__.py
│   │   ├── tools/
│   │   │   ├── transaction_tool.py # Deterministic transaction CRUD/search operations
│   │   │   ├── analytics_tool.py   # Spending summary, daily trend, top transactions, and period comparison
│   │   │   ├── budget_tool.py      # Monthly and category budget upsert/read operations
│   │   │   ├── forecast_tool.py    # Month-end spending forecast and budget-risk calculation
│   │   │   ├── advice_tool.py      # Data-grounded spending advice and alerts
│   │   │   └── __init__.py
│   │   ├── main.py                 # FastAPI app factory, CORS setup, router registration, DB table creation
│   │   └── __init__.py
│   ├── tests/
│   │   └── test_agent_flow.py      # End-to-end API tests for agent chat, budget/forecast, and RAG retrieval
│   └── requirements.txt            # Backend Python dependencies
├── docs/
│   └── architecture.md             # Architecture notes and safety/design principles
├── frontend/
│   ├── app.py                      # Streamlit dashboard for chat, transactions, budgets, analytics, and insights
│   └── requirements.txt            # Frontend Python dependencies
├── docker-compose.yml              # Local service orchestration placeholder/configuration
├── ai_expense_agent_readme.md      # Extended Japanese design/readme draft
└── README.md                       # Main project documentation
```

### Folder and File Roles / 各フォルダ・ファイルの役割

**`backend/app/agents/`**

Agentの中核です。`orchestrator.py` がLangGraphの状態遷移を管理し、`memory.py` で短期メモリ、`rag.py` で関連コンテキスト検索、`llm_client.py` でOpenAI Structured OutputsとFunction Callingを扱います。APIキーが空、またはLLM呼び出しに失敗した場合は、`parser.py` と `tool_registry.py` を通じてローカルの決定的な処理にフォールバックします。

**`backend/app/tools/`**

実際にデータを作成・集計・予測する決定的ツール群です。LLMは数値を直接作らず、ここにある `transaction_tool.py`、`analytics_tool.py`、`budget_tool.py`、`forecast_tool.py`、`advice_tool.py` を選択して呼び出します。これにより、家計データの計算結果を追跡しやすくしています。

**`backend/app/api/`**

FastAPIのHTTP入口です。`routes.py` にチャット、取引CRUD、分析、予算、予測、助言、CSVエクスポートのエンドポイントがまとまっています。フロントエンドや外部クライアントは基本的にこの層を通じてバックエンド機能を利用します。

**`backend/app/models/` and `backend/app/schemas/`**

`models.py` はSQLiteに保存されるSQLAlchemyモデルを定義します。`schemas.py` はAPI入出力とAgentツール入力のPydanticバリデーションを担当します。LLM Structured Outputsで抽出された値も、最終的にはPydantic schemaを通ってからDBに保存されます。

**`backend/app/core/`, `repositories/`, and `services/`**

`core/` は設定とDB接続、`repositories/` はユーザー取得などのデータアクセス補助、`services/` はカテゴリ判定や日付計算などの再利用可能なドメインロジックを提供します。AgentやToolsから共通利用される土台です。

**`frontend/`**

Streamlit製のダッシュボードです。チャット入力、取引一覧、予算、分析結果などをブラウザ上で操作・確認できます。バックエンドAPIを呼び出す薄いUI層として分離しています。

**`docs/` and root files**

`docs/architecture.md` は設計思想、Agent構成、安全方針を説明します。`README.md` は実行方法と機能概要、`ai_expense_agent_readme.md` は詳細な日本語設計メモ、`docker-compose.yml` はローカル実行構成のための設定ファイルです。

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

OpenAI APIキーは任意です。空のままでも動作します。LLM Structured Outputsを有効にする場合は、リポジトリルートまたは `backend` 配下の `.env` に以下を設定します。

```bash
EXPENSE_OPENAI_API_KEY=
EXPENSE_OPENAI_MODEL=gpt-4.1-mini
EXPENSE_AGENT_MEMORY_LIMIT=8
EXPENSE_RAG_TOP_K=5
```

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

- 複合命令の分解とマルチステップ実行の強化
- 異常支出検知と時系列予測モデル
- 分類・予測精度の定量評価
- ユーザー認証とマルチユーザー対応
- PostgreSQLおよびクラウド環境への移行
- Docker化とCI/CD
