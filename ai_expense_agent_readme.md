# AI Expense Agent V3 設計ドキュメント

## 1. プロジェクト概要

### 1.1 プロジェクト名

**AI Expense Agent**

### 1.2 V3 の目標

V3 は単なる「自然言語の家計簿入力ツール」ではなく、ユーザーの支出状況を継続的に理解し、予算リスクを予測し、個別化された提案を行う軽量な財務 Agent を目指す。

主な目標：

1. ユーザーが自然言語で支出と収入をすばやく記録できる。
2. システムが金額、日付、店舗、カテゴリ、メモを自動解析する。
3. 日次、週次、月次の支出統計をサポートする。
4. 支出変化の原因を分析できる。
5. 月末支出と予算超過リスクを予測できる。
6. 説明可能な支出改善提案を能動的に生成できる。
7. 重要な計算はすべてバックエンドプログラムで行い、LLM は理解、説明、提案に限定することで、モデルが数字を勝手に作ることを防ぐ。

---

## 2. V3 のコア機能

### 2.1 自然言語による記録

ユーザー入力：

```text
今日の昼食でラーメンに980円使った
```

システム解析結果：

```json
{
  "type": "expense",
  "amount": 980,
  "currency": "JPY",
  "category": "food",
  "merchant": "ラーメン店",
  "date": "2026-07-19",
  "note": "昼食でラーメン",
  "confidence": 0.96
}
```

対応する入力例：

```text
昨日、地下鉄で420円使った
さっきAmazonで本を3280円で買った
今月の家賃85000円
今日、インターン給与45000円を受け取った
先週金曜、友達との食事で3600円使った
```

システムが認識すべき項目：

- 支出または収入
- 金額
- 通貨
- 日付
- カテゴリ
- 店舗
- 自然言語メモ
- 解析信頼度

### 2.2 自動分類

デフォルトカテゴリ：

| カテゴリコード | 表示名 | 例 |
|---|---|---|
| food | 飲食 | ラーメン、コーヒー、デリバリー |
| transport | 交通 | 地下鉄、バス、タクシー |
| shopping | 買い物 | Amazon、服、電子製品 |
| housing | 住居 | 家賃、水道光熱費、家具 |
| entertainment | 娯楽 | 映画、ゲーム、飲み会 |
| education | 学習 | 書籍、講座、学会登録 |
| health | 健康 | 薬、病院、ジム |
| subscription | サブスクリプション | ChatGPT、Netflix、クラウドサービス |
| travel | 旅行 | ホテル、航空券、ビザ |
| social | 交際 | 食事会、プレゼント |
| salary | 給与収入 | インターン給与、アルバイト給与 |
| reimbursement | 精算 | 会社精算、学校精算 |
| other | その他 | 分類できない取引 |

分類の優先順位：

1. ユーザーが明示したカテゴリ。
2. 店舗ルールの一致。
3. キーワードルールの一致。
4. LLM による分類。
5. 判定できない場合は `other` に分類する。

### 2.3 支出統計

対応する問い合わせ：

```text
今日は合計いくら使った？
今月の飲食費はいくら？
今週の大きい支出トップ3は？
今月の収入と支出はそれぞれいくら？
直近30日の1日平均支出はいくら？
```

出力は LLM が自分で計算した数字ではなく、必ずデータベース計算結果に基づく必要がある。

### 2.4 支出変化分析

ユーザーは以下のように質問できる：

```text
なぜ今月は先月より支出が多いの？
最近、飲食費が増えた理由は？
今月いちばん増えた支出カテゴリは？
```

バックエンドが最初に計算する項目：

- 現在期間の総支出
- 比較期間の総支出
- カテゴリ別差額
- カテゴリ別増加率
- 高額取引数
- 新規店舗または新規サブスクリプション
- 取引頻度の変化

その後、構造化された分析結果を LLM に渡し、自然言語の説明を生成する。

出力例：

```text
今月は現時点で、先月同期間より12,400円多く支出しています。主な要因は3つです。

1. 買い物支出が6,800円増えています。主な理由はAmazonでの書籍購入です。
2. 飲食費が3,900円増えています。外食回数が8回から13回に増えました。
3. 今月、新たに1,700円のサブスクリプション支出が発生しています。

今月もっとも増加しているカテゴリは買い物です。
```

### 2.5 予算管理

ユーザーが設定できる項目：

- 月間総予算
- カテゴリ別予算
- 固定支出
- 貯蓄目標

例：

```text
今月の総予算を12万円にして
飲食予算を3万円にして
買い物は最大1万5千円
毎月少なくとも5万円貯金したい
```

予算データ：

```json
{
  "month": "2026-07",
  "total_budget": 120000,
  "saving_target": 50000,
  "category_budgets": {
    "food": 30000,
    "shopping": 15000,
    "entertainment": 10000
  }
}
```

### 2.6 月末支出予測

システムは、当月の経過日数と支出データに基づいて月末支出を予測する。

基本予測：

```text
月末予測支出 = 現在の累計支出 / 経過日数 × 当月の日数
```

改善版予測：

```text
月末予測支出 = 固定支出 + 可変支出の日平均 × 残日数
```

定義：

- 固定支出：家賃、サブスクリプション、固定請求など。
- 可変支出：飲食、買い物、娯楽、交通など。
- 日平均は直近7日、14日、または当月平均を利用できる。
- データが不足している場合は基本予測へフォールバックする。

予測出力：

```json
{
  "current_spending": 78000,
  "predicted_month_end_spending": 132500,
  "monthly_budget": 120000,
  "predicted_over_budget": 12500,
  "risk_level": "high"
}
```

リスクレベル：

| レベル | 条件 |
|---|---|
| low | 予測支出が予算の85%未満 |
| medium | 予測支出が予算の85%以上100%以下 |
| high | 予測支出が予算を超過 |
| critical | 予算超過見込みが15%を超える |

### 2.7 スマート提案

Agent の提案は必ず実データに基づく。

例：

```text
現在のペースでは、月末に約12,500円の予算超過となる可能性があります。

調整しやすい項目は飲食と買い物です。
- 今月は残り12日です。1日の可変支出を2,300円以内に抑えることをおすすめします。
- 飲食予算は残り6,400円で、1日平均では約533円です。
- 今月は不要不急の買い物が2件あり、合計8,200円です。
```

提案タイプ：

- 予算アラート
- カテゴリ別超過通知
- 高額支出の注意喚起
- 重複サブスクリプションの注意
- 支出頻度の異常検知
- 月末残高予測
- 貯蓄目標リスク
- 1日あたり利用可能予算の提案

### 2.8 能動的な通知

V3 では、複雑なバックグラウンドプッシュではなく、「App 起動時に通知を生成する」形から実装してよい。

通知トリガー：

- 特定カテゴリの利用率が予算の80%を超えた
- 総予算の利用率が80%を超えた
- 月末に予算超過が予測される
- 1件の支出がユーザー定義のしきい値を超えた
- 連続して高支出の日が続いた
- サブスクリプションの引き落としが近い
- 今週の支出が過去4週間平均を大きく上回る

例：

```text
予算通知：飲食予算の87%を使用しています。今月は残り12日です。
```

---

## 3. プロダクト範囲

### 3.1 V3 で必ず実装する機能

- 自然言語による支出・収入の追加
- 手動での取引追加、編集、削除
- 自動分類
- 日次、週次、月次統計
- カテゴリ別グラフ
- 月間予算設定
- カテゴリ別予算設定
- 今月と先月の比較
- 月末支出予測
- 予算超過リスク評価
- AI 支出分析
- AI 節約提案
- CSV データエクスポート

### 3.2 V3 では実装しない機能

- 銀行口座との直接連携
- クレジットカード API の自動同期
- Apple Wallet の自動読み取り
- 自動決済
- 株式投資アドバイス
- 税務申告
- 複数人での共有家計簿
- 複数通貨のリアルタイム為替
- 完全自動のバックグラウンド通知

これらの機能はコストとコンプライアンスの複雑度が高いため、V4 以降に回す。

---

## 4. ユーザーシナリオ

### シナリオ1：すばやく記録する

ユーザー：

```text
今日の夕食で友達と焼肉を食べて4200円使った
```

Agent：

```text
記録しました：
- 金額：4,200円
- カテゴリ：交際
- 日付：2026年7月19日
- メモ：友達と焼肉
```

### シナリオ2：今月の支出を確認する

ユーザー：

```text
今月いくら使った？
```

Agent：

```text
今月の現時点の総支出は78,300円です。主なカテゴリは以下です。
- 住居：40,000円
- 飲食：18,600円
- 交通：7,800円
- 買い物：6,900円
```

### シナリオ3：支出増加の理由を分析する

ユーザー：

```text
なぜ今月の支出は先月より高いの？
```

Agent：

```text
今月は先月同期間より9,700円多く支出しています。
主な理由は、買い物が5,200円、飲食が3,100円増えていることです。
買い物の増加は、Amazonでの書籍購入と電子製品の支出が主な要因です。
```

### シナリオ4：予算を予測する

ユーザー：

```text
今月は予算を超えそう？
```

Agent：

```text
現在の支出ペースでは、月末の総支出は約132,500円と予測されます。
予算は120,000円なので、約12,500円超過する見込みです。リスクレベルは高です。
```

### シナリオ5：節約提案を受ける

ユーザー：

```text
12万円以内に抑えるにはどうしたらいい？
```

Agent：

```text
今月は残り12日で、12万円以内に抑えるには残り約41,700円まで使えます。
提案：
1. 1日の可変支出を2,300円以内に抑える。
2. 不要不急の買い物を一時停止すると、約8,000円削減できる見込みです。
3. 飲食予算は残り6,400円なので、外食回数を減らすことをおすすめします。
```

---

## 5. システムアーキテクチャ

```text
Web / Mobile UI
      ↓
FastAPI Backend
      ↓
Agent Orchestrator
      ├── Intent Parser
      ├── Transaction Tool
      ├── Analytics Tool
      ├── Budget Tool
      ├── Forecast Tool
      └── Advice Generator
      ↓
SQLite / PostgreSQL
      ↓
LLM API
```

### 5.1 設計原則

1. **データベースを事実のソースとする。**
2. **金額計算は Python で行う。**
3. **LLM はデータベースを直接変更しない。**
4. **LLM は制御された Tool Calling を通じてのみ操作を行う。**
5. **すべての書き込み操作はログを残す。**
6. **信頼度の低い解析はユーザー確認を必要とする。**

---

## 6. Agent のワークフロー

### 6.1 意図認識

ユーザー入力は最初に以下へ分類する：

```text
ADD_TRANSACTION
UPDATE_TRANSACTION
DELETE_TRANSACTION
QUERY_SUMMARY
COMPARE_PERIOD
SET_BUDGET
FORECAST_SPENDING
GENERATE_ADVICE
UNKNOWN
```

### 6.2 Agent Loop

```text
ユーザー入力
  ↓
意図認識
  ↓
パラメータ抽出
  ↓
パラメータ検証
  ↓
ツール選択
  ↓
データベース処理または分析関数の実行
  ↓
結果確認
  ↓
自然言語の返答生成
```

### 6.3 Tool 定義

#### add_transaction

```json
{
  "type": "expense",
  "amount": 980,
  "currency": "JPY",
  "category": "food",
  "merchant": "一蘭",
  "transaction_date": "2026-07-19",
  "note": "昼食"
}
```

#### query_spending_summary

```json
{
  "start_date": "2026-07-01",
  "end_date": "2026-07-31",
  "group_by": "category"
}
```

#### compare_periods

```json
{
  "current_start": "2026-07-01",
  "current_end": "2026-07-19",
  "previous_start": "2026-06-01",
  "previous_end": "2026-06-19"
}
```

#### set_budget

```json
{
  "month": "2026-07",
  "category": "food",
  "amount": 30000
}
```

#### forecast_month_end

```json
{
  "month": "2026-07",
  "method": "fixed_plus_variable"
}
```

#### generate_spending_advice

入力には、バックエンドで計算済みの構造化結果を必ず含める：

```json
{
  "budget": 120000,
  "current_spending": 78000,
  "predicted_spending": 132500,
  "remaining_days": 12,
  "top_growth_categories": [
    {
      "category": "shopping",
      "difference": 6800
    }
  ]
}
```

---

## 7. データベース設計

### 7.1 users

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    default_currency TEXT NOT NULL DEFAULT 'JPY',
    timezone TEXT NOT NULL DEFAULT 'Asia/Tokyo',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 7.2 transactions

```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('expense', 'income')),
    amount INTEGER NOT NULL CHECK(amount >= 0),
    currency TEXT NOT NULL DEFAULT 'JPY',
    category TEXT NOT NULL,
    merchant TEXT,
    note TEXT,
    transaction_date DATE NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    is_fixed INTEGER NOT NULL DEFAULT 0,
    confidence REAL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
```

金額は最小通貨単位の整数で保存することを推奨する。JPY はそのまま整数で扱える。

### 7.3 budgets

```sql
CREATE TABLE budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    month TEXT NOT NULL,
    category TEXT,
    amount INTEGER NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, month, category),
    FOREIGN KEY(user_id) REFERENCES users(id)
);
```

`category = NULL` は月間総予算を表す。

### 7.4 saving_goals

```sql
CREATE TABLE saving_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    month TEXT NOT NULL,
    target_amount INTEGER NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, month),
    FOREIGN KEY(user_id) REFERENCES users(id)
);
```

### 7.5 recurring_transactions

```sql
CREATE TABLE recurring_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    amount INTEGER NOT NULL,
    category TEXT NOT NULL,
    merchant TEXT,
    recurrence_rule TEXT NOT NULL,
    next_date DATE,
    active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
```

### 7.6 agent_logs

```sql
CREATE TABLE agent_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    user_message TEXT NOT NULL,
    detected_intent TEXT,
    tool_name TEXT,
    tool_input TEXT,
    tool_output TEXT,
    success INTEGER NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
```

---

## 8. API 設計

### 8.1 Agent 対話

```http
POST /api/v1/agent/chat
```

リクエスト：

```json
{
  "message": "今日の昼食で980円使った"
}
```

レスポンス：

```json
{
  "intent": "ADD_TRANSACTION",
  "message": "今日の昼食支出980円を記録しました。",
  "data": {
    "transaction_id": 101,
    "amount": 980,
    "category": "food"
  }
}
```

### 8.2 取引管理

```http
GET    /api/v1/transactions
POST   /api/v1/transactions
PATCH  /api/v1/transactions/{id}
DELETE /api/v1/transactions/{id}
```

### 8.3 支出統計

```http
GET /api/v1/analytics/summary
GET /api/v1/analytics/categories
GET /api/v1/analytics/trend
GET /api/v1/analytics/compare
GET /api/v1/analytics/top-transactions
```

### 8.4 予算管理

```http
GET  /api/v1/budgets/{month}
POST /api/v1/budgets
PUT  /api/v1/budgets/{id}
```

### 8.5 予測と提案

```http
GET  /api/v1/forecast/{month}
POST /api/v1/advice/generate
GET  /api/v1/alerts
```

### 8.6 データエクスポート

```http
GET /api/v1/export/csv
```

---

## 9. 画面設計

### 9.1 ダッシュボード

表示項目：

- 今月の総支出
- 今月の総収入
- 予算残高
- 月末予測支出
- 予算超過リスク
- カテゴリ別比率グラフ
- 日別支出トレンド
- 最近の取引
- Agent 通知

### 9.2 チャット画面

自然言語入力をサポートする：

```text
今日コーヒー480円
今月いくら使った？
なぜ先月より高い？
飲食予算を3万円に変更して
```

### 9.3 取引画面

対応機能：

- 取引表示
- 検索
- 日付による絞り込み
- カテゴリによる絞り込み
- 編集
- 削除
- CSV エクスポート

### 9.4 予算画面

表示項目：

- 総予算
- カテゴリ別予算
- 使用済み金額
- 使用率
- 残り予算
- 月末予測金額

### 9.5 分析画面

表示項目：

- 今月と先月の比較
- 増加率が最も高いカテゴリ
- 主な支出変化の原因
- 高額支出
- 異常支出
- AI 提案

---

## 10. 予測アルゴリズム

### 10.1 基本版

```python
predicted = current_spending / elapsed_days * total_days
```

### 10.2 推奨版

```python
predicted = fixed_costs + average_variable_daily_spending * remaining_days + current_variable_spending
```

推奨ルール：

1. 当月の固定支出を識別する。
2. 直近14日の可変支出の日平均を計算する。
3. データが7日未満の場合は、当月の日平均を使う。
4. 極端な高額支出は外れ値処理し、1回の購入が予測を大きく歪めることを避ける。
5. 楽観、中立、悲観の区間を同時に返す。

例：

```json
{
  "optimistic": 118000,
  "expected": 132500,
  "pessimistic": 145000
}
```

---

## 11. AI プロンプト設計

### 11.1 取引解析 Prompt

```text
あなたは個人家計簿システムの取引解析器です。
ユーザー入力から取引情報を抽出し、厳密に JSON を返してください。

ルール：
1. 金額を捏造してはいけません。
2. 通貨がない場合は JPY をデフォルトにしてください。
3. ユーザーのタイムゾーン Asia/Tokyo に基づいて「今日、昨日、先週金曜」などの日付を解析してください。
4. カテゴリが判定できない場合は other を返してください。
5. 重要フィールドが判定できない場合は missing_fields に入れてください。
6. データベース操作は実行しないでください。
```

### 11.2 支出提案 Prompt

```text
あなたは個人支出分析アシスタントです。
すべての数字はバックエンド計算結果に由来します。変更、再計算、捏造は禁止です。
予算、予測、カテゴリ変化、取引頻度に基づいて、簡潔で実行可能な提案を生成してください。

要件：
1. 最も重要な1〜3個の理由を明確に示してください。
2. 実行可能な提案を出してください。
3. 株式、投資、ローンの助言は提供しないでください。
4. 侮辱、非難、過度に不安を煽る口調は避けてください。
5. 事実、予測、提案を明確に区別してください。
```

---

## 12. 安全性と信頼性

### 12.1 データ安全性

- デフォルトはローカル SQLite。
- 銀行カードのパスワードは保存しない。
- クレジットカード番号の全桁は保存しない。
- API Key は環境変数に保存する。
- ログでは機密情報をマスクする。
- エクスポートファイルはユーザー操作でのみ生成する。

### 12.2 LLM 安全性

- JSON Schema または Structured Outputs を使用する。
- Tool 引数は Pydantic で検証する。
- 取引削除前には二次確認を行う。
- 高額な異常解析は確認を必要とする。
- Agent は SQL を直接実行してはいけない。
- すべてのデータベース操作は固定ツールとしてラップする。

### 12.3 財務免責

このシステムは個人の支出記録と予算補助のみを目的とし、投資、税務、法律、専門的な財務助言を構成しない。

---

## 13. 推奨技術スタック

### バックエンド

- Python 3.12
- FastAPI
- SQLAlchemy 2.0
- Pydantic
- SQLite
- Alembic

### Agent

- OpenAI API または Gemini API
- Function Calling / Structured Outputs
- 独自の軽量 Agent Orchestrator

初版では LangGraph、CrewAI、複雑なマルチ Agent フレームワークは必須ではない。

### フロントエンド

最短で作る案：

- Streamlit

ポートフォリオを強化する案：

- Next.js
- TypeScript
- Tailwind CSS
- ECharts または Recharts

### テスト

- pytest
- FastAPI TestClient

### デプロイ

低コスト案：

- フロントエンド：Vercel
- バックエンド：Render / Railway
- データベース：SQLite 単体、または Supabase PostgreSQL

---

## 14. プロジェクトディレクトリ案

```text
ai-expense-agent/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── agents/
│   │   │   ├── orchestrator.py
│   │   │   ├── parser.py
│   │   │   └── prompts.py
│   │   ├── tools/
│   │   │   ├── transaction_tool.py
│   │   │   ├── analytics_tool.py
│   │   │   ├── budget_tool.py
│   │   │   ├── forecast_tool.py
│   │   │   └── advice_tool.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   └── core/
│   ├── tests/
│   ├── alembic/
│   └── requirements.txt
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
├── docs/
│   └── architecture.md
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## 15. 開発順序

### Phase 1：基礎データ層

- FastAPI プロジェクトを作成する。
- SQLite データベースを作成する。
- Transaction CRUD を実装する。
- Budget CRUD を実装する。
- テストデータを作成する。

### Phase 2：自然言語記録

- 取引解析 Prompt を実装する。
- Structured Outputs を使用する。
- `add_transaction` Tool を実装する。
- 低信頼度時の確認フローを実装する。

### Phase 3：統計分析

- 日次、週次、月次統計
- カテゴリ統計
- トレンド統計
- 現在期間と前期間の比較
- 高額取引分析

### Phase 4：予算と予測

- 総予算とカテゴリ予算
- 固定支出識別
- 月末支出予測
- リスクレベル計算
- 1日あたり利用可能予算の計算

### Phase 5：AI Insights

- 支出増加理由の要約
- 予算超過理由の要約
- 個別化された節約提案
- 能動的通知生成

### Phase 6：フロントエンドとデプロイ

- Dashboard
- Chat
- Transactions
- Budget
- Insights
- CSV エクスポート
- デプロイ

---

## 16. 受け入れ基準

### 自然言語解析

- 一般的な日本語の家計簿文を90%以上の成功率で解析できる。
- 金額はモデルが捏造してはいけない。
- 相対日付を具体的な日付へ正しく変換できる。

### 統計

- すべての統計結果がデータベース SQL の結果と一致する。
- 日次、週次、月次の絞り込みが正確である。
- カテゴリ合計が総支出と一致する。

### 予算予測

- 現在支出、予測支出、予算差額、リスクレベルを返せる。
- データ不足時は予測の信頼度が低いことを明示する。

### AI 提案

- 提案内の数字はすべてバックエンド結果まで追跡できる。
- 少なくとも1つの具体的で実行可能な提案を出す。
- 投資やローンの助言を生成しない。

### 安定性

- LLM API が失敗しても既存の家計簿データに影響しない。
- 重複送信による二重記録を防ぐ。
- 削除操作には確認を必要とする。

---

## 17. 履歴書記載例

```text
Developed an AI-powered expense management agent using FastAPI, SQLite and LLM function calling. The system supports natural-language transaction entry, automatic categorization, budget tracking, month-end spending forecasting, period-over-period analysis and explainable personalized spending recommendations. All financial calculations are performed by deterministic backend tools, while the LLM is restricted to intent understanding and natural-language explanation.
```

日本語版：

```text
FastAPI、SQLite、LLM Function Callingを用いたAI家計管理Agentを開発。自然言語による支出登録、自動カテゴリ分類、予算管理、月末支出予測、前月比較、支出増加要因の分析および説明可能な節約提案を実装した。金額計算はすべてバックエンド側で決定論的に処理し、LLMは意図理解と自然言語説明に限定することで信頼性を確保した。
```

---

## 18. 最終 MVP 定義

V3 完成時、ユーザーは以下の一連の流れを完了できるべきである。

```text
「今日の昼食980円」
        ↓
自動記録と分類
        ↓
「今月いくら使った？」
        ↓
実データに基づく統計を返す
        ↓
「なぜ先月より多い？」
        ↓
主な増加カテゴリと取引を説明する
        ↓
「月末に予算を超えそう？」
        ↓
予測とリスクレベルを生成する
        ↓
「12万円以内に抑えるには？」
        ↓
データに基づく実行可能な提案を出す
```

これが V3 のコアな閉ループである：

> **記録 → 統計 → 比較 → 予測 → 提案。**

---

# 19. 汎用 AI Agent 技術体系と本プロジェクトの対応関係

本章では、本プロジェクトと汎用 AI Agent 技術体系の関係を説明し、V3 で採用する技術、採用しない技術、そのエンジニアリング上の理由を明確にする。

## 19.1 全体結論

本プロジェクトは、Agent 関連技術をすべて積み上げるものではなく、Expense Agent の業務目的を中心に取捨選択する。

V3 のコア原則：

> **1つのメイン Agent + 複数の決定論的 Python / SQL Tools。**

役割分担：

- LLM はユーザー意図の理解、パラメータ抽出、ツール選択、自然言語説明を担当する。
- バックエンドツールは金額計算、予算判断、トレンド分析、予測、データベース書き込みを担当する。
- データベースは取引、予算、嗜好、履歴状態を保存する。
- Agent 編成層は状態管理、条件分岐、確認、エラー復旧、中断後の再開を担当する。

したがって、V3 で重点的に採用するもの：

- LLM API
- Structured Output
- Function Calling / Tool Use
- LangGraph
- Short-term Memory
- Long-term Memory
- Checkpointer
- ルール検証と軽量 Self-Reflection
- SQL / Python による決定論的分析

V3 で必須としないもの：

- 完全な RAG
- ベクトルデータベース
- CrewAI / AutoGen のマルチ Agent
- MCP Server

これらは V4 以降に必要に応じて追加する。

---

## 19.2 LLM API とモデル抽象化

### 19.2.1 本プロジェクトにおける LLM の責務

LLM が担当するタスク：

1. 意図分類
2. 取引フィールド抽出
3. ツール選択
4. 不足情報の確認質問
5. ツール結果に基づく自然言語説明
6. ユーザー要求の複数ステップへの分解

LLM が担当しないタスク：

- 月間総支出を直接計算すること。
- データベース内の金額を推測すること。
- 予算結論をツールなしで生成すること。
- ツール根拠なしに超過有無を判断すること。
- バックエンドを迂回してデータベースを直接変更すること。

### 19.2.2 Provider 抽象

特定モデル名を業務コードへ直書きしない。以下のような統一インターフェースを定義することを推奨する。

```python
from typing import Protocol, Any


class LLMProvider(Protocol):
    async def generate_structured_output(
        self,
        *,
        messages: list[dict[str, str]],
        schema: type,
    ) -> Any:
        ...

    async def call_tools(
        self,
        *,
        messages: list[dict[str, str]],
        tools: list[dict],
    ) -> Any:
        ...
```

設定例：

```yaml
llm:
  provider: openai
  model: ${LLM_MODEL}
  temperature: 0
  max_retries: 2
  timeout_seconds: 30
```

この設計により、業務ロジックを変更せずにモデルプロバイダを差し替えられる。

### 19.2.3 運用上の注意点

考慮すべき項目：

- Token 消費の監視
- Rate Limit 時のリトライ
- 指数バックオフ
- タイムアウト処理
- コンテキストウィンドウの切り詰め
- 履歴メッセージの要約
- リクエストログ
- モデル失敗時のフォールバック戦略

記録を推奨する指標：

```text
request_count
input_tokens
output_tokens
estimated_cost
latency_ms
retry_count
provider_error_type
```

---

# 20. LangGraph アーキテクチャ設計

## 20.1 V3 で LangGraph を採用する理由

V3 は LangGraph に必ず依存する必要はなく、純粋な Python 状態機械でも実装できる。ただし、プロジェクト目標に以下が含まれるなら LangGraph は適している。

- Agent エンジニアリングを学ぶ
- 状態管理能力を示す
- 中断復帰をサポートする
- Human-in-the-loop をサポートする
- 複数ステップのツール呼び出しをサポートする
- 条件分岐とエラー復旧をサポートする

## 20.2 4つのコア概念と本プロジェクトの対応

### State

State は Agent ワークフロー全体を流れるデータである。

```python
from typing import TypedDict, Any


class ExpenseAgentState(TypedDict, total=False):
    user_id: int
    thread_id: str
    messages: list[dict[str, str]]
    user_input: str

    intent: str | None
    extracted_params: dict[str, Any]
    validation_errors: list[str]

    selected_tool: str | None
    tool_arguments: dict[str, Any]
    tool_result: dict[str, Any] | None

    requires_confirmation: bool
    confirmation_status: str | None
    retry_count: int

    current_topic: str | None
    current_period: str | None
    response: str | None
```

### Nodes

推奨ノード：

```text
load_context
classify_intent
extract_parameters
validate_parameters
route_intent
execute_tool
check_result
request_clarification
request_confirmation
recover_error
generate_response
save_memory
```

### Edges

通常エッジは固定フローを表す。

```text
START
  ↓
load_context
  ↓
classify_intent
  ↓
extract_parameters
```

### Conditional Edges

条件エッジは状態に基づいて次のステップを決める。

```python
def route_after_validation(state: ExpenseAgentState) -> str:
    if state.get("validation_errors"):
        return "request_clarification"

    if state.get("requires_confirmation"):
        return "request_confirmation"

    return "execute_tool"
```

## 20.3 推奨ワークフロー

```text
START
  ↓
Load Context
  ↓
Intent Parser
  ↓
Parameter Extractor
  ↓
Validator
  ↓
Conditional Route
  ├── パラメータ不足 → Clarification
  ├── 高リスク操作 → Confirmation
  ├── 通常問い合わせ → Query Tool
  ├── 取引書き込み → Transaction Tool
  ├── 予算操作 → Budget Tool
  ├── トレンド分析 → Analytics Tool
  └── 月末予測 → Forecast Tool
          ↓
Result Checker
  ├── データ不足 → Clarification
  ├── ツール失敗 → Error Recovery
  ├── 結果異常 → Re-evaluate
  └── 正常 → Response Generator
                      ↓
                  Save Memory
                      ↓
                     END
```

## 20.4 LangGraph 擬似コード

```python
from langgraph.graph import StateGraph, START, END


graph = StateGraph(ExpenseAgentState)

graph.add_node("load_context", load_context)
graph.add_node("classify_intent", classify_intent)
graph.add_node("extract_parameters", extract_parameters)
graph.add_node("validate_parameters", validate_parameters)
graph.add_node("execute_tool", execute_tool)
graph.add_node("check_result", check_result)
graph.add_node("request_clarification", request_clarification)
graph.add_node("request_confirmation", request_confirmation)
graph.add_node("recover_error", recover_error)
graph.add_node("generate_response", generate_response)
graph.add_node("save_memory", save_memory)

graph.add_edge(START, "load_context")
graph.add_edge("load_context", "classify_intent")
graph.add_edge("classify_intent", "extract_parameters")
graph.add_edge("extract_parameters", "validate_parameters")

graph.add_conditional_edges(
    "validate_parameters",
    route_after_validation,
    {
        "request_clarification": "request_clarification",
        "request_confirmation": "request_confirmation",
        "execute_tool": "execute_tool",
    },
)

graph.add_edge("execute_tool", "check_result")

graph.add_conditional_edges(
    "check_result",
    route_after_result_check,
    {
        "recover_error": "recover_error",
        "request_clarification": "request_clarification",
        "generate_response": "generate_response",
    },
)

graph.add_edge("generate_response", "save_memory")
graph.add_edge("save_memory", END)
```

---

# 21. Function Calling / Tool Use 設計

## 21.1 基本フロー

```text
1. 開発者が Tool Schema を定義する
2. LLM が呼び出す Tool を判断する
3. バックエンドが引数を検証する
4. バックエンドが実際の関数を実行する
5. Tool Result を Agent に返す
6. Agent が結果に基づいて返答を生成する
```

## 21.2 例：予算設定

ユーザー入力：

```text
今月の飲食予算を3万円に設定して
```

LLM が生成するツール呼び出し：

```json
{
  "tool": "set_budget",
  "arguments": {
    "month": "2026-07",
    "category": "food",
    "amount": 30000,
    "currency": "JPY"
  }
}
```

バックエンド実行：

```python
result = set_budget(
    user_id=user_id,
    month="2026-07",
    category="food",
    amount=30000,
    currency="JPY",
)
```

Tool Result：

```json
{
  "success": true,
  "month": "2026-07",
  "category": "food",
  "amount": 30000,
  "currency": "JPY"
}
```

最終返信：

```text
2026年7月の飲食予算を30,000円に設定しました。
```

## 21.3 推奨 Tools

### 取引系

```text
create_transaction
update_transaction
delete_transaction
list_transactions
find_possible_duplicates
```

### 予算系

```text
set_budget
get_budget_status
list_budgets
update_budget
```

### 分析系

```text
get_period_summary
compare_periods
get_category_breakdown
get_large_transactions
get_spending_trend
```

### 予測系

```text
forecast_month_end
estimate_remaining_budget
calculate_safe_daily_spending
```

### ユーザー嗜好系

```text
set_user_preference
get_user_preferences
set_merchant_category_rule
```

## 21.4 安全ルール

以下の操作は必ず確認を必要とする：

- 取引の削除
- 取引の一括変更
- 一括インポートによる上書き
- 過去月の予算変更
- ユーザーデータの全削除
- 完全な財務記録のエクスポート

原則：

> LLM はツール呼び出しのリクエストだけを出せる。バックエンド検証を迂回して高リスク操作を直接実行してはいけない。

---

# 22. Memory Management

## 22.1 短期記憶

短期記憶は現在の会話文脈を維持するために使う。

例：

```text
ユーザー：今月の飲食費はいくら？
Agent：18,600円です。
ユーザー：じゃあ先月は？
```

システムは以下を理解する必要がある：

```text
「それ」 = 飲食支出
比較期間 = 先月
```

State に保存する項目の例：

```python
current_topic = "food spending"
current_period = "2026-07"
previous_intent = "QUERY_CATEGORY_SPENDING"
```

実装方式：

- 直近 N ターンのメッセージウィンドウ
- 現在セッションの State
- 長い会話の要約
- LangGraph Checkpointer

## 22.2 長期記憶

長期記憶は2種類に分ける。

### 構造化された業務記憶

SQL データベースに保存する：

```text
ユーザーのデフォルト通貨
ユーザーのタイムゾーン
予算
取引
貯蓄目標
固定支出
店舗カテゴリルール
通知しきい値
```

この種類の情報は、ベクトルデータベースで置き換えるべきではない。

### 非構造化の嗜好記憶

例：

```text
友達との食事は普通の飲食ではなく交際にする。
1,000円未満の金額では頻繁に通知しない。
回答はできるだけ簡潔にする。
毎月25日が給与日。
```

まずは構造化して保存することを推奨する：

```json
{
  "preference_key": "meal_with_friends_category",
  "preference_value": "social"
}
```

嗜好の数が非常に多く、構造化が難しい場合のみベクトル検索を検討する。

## 22.3 推奨データテーブル

```sql
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    preference_key TEXT NOT NULL,
    preference_value TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    source TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    UNIQUE(user_id, preference_key)
);
```

## 22.4 LangGraph Checkpointer

Checkpointer は、各ノード実行後の State スナップショットを保存するために使う。

実現できること：

- 中断復帰
- Human-in-the-loop
- エラー後のリトライ
- 確認ノードからの再開
- 過去状態のデバッグ
- Agent 実行軌跡の確認

本番環境ではデータベース型 Checkpointer を推奨し、ローカル開発ではメモリまたは SQLite から始めてよい。

## 22.5 Summarization Memory

会話が長くなった場合：

```text
完全な履歴メッセージ
↓
要約ノード
↓
重要な事実、未完了タスク、ユーザー嗜好を保持
↓
冗長な履歴を削除
```

要約に含めるべき内容：

- 現在の議論テーマ
- 確認済みの事実
- 未完了の操作
- 重要なユーザー嗜好
- 直近のツール結果
- 確認待ちのリスク操作

---

# 23. Planning、Reasoning、Self-Reflection

## 23.1 本プロジェクトにおける ReAct の適用

ユーザーが質問する：

```text
なぜ今月は先月より支出が多いの？
```

Agent が実行すべき流れ：

```text
Reason：2つの自然月を比較する必要がある
Act：compare_periods を呼び出す
Observe：今月は9,700円多い
Reason：主な増加カテゴリを知る必要がある
Act：get_category_breakdown を呼び出す
Observe：買い物 +6,800、食事会 +3,500
Reason：代表的な取引を見つける必要がある
Act：get_large_transactions を呼び出す
Observe：Amazon 6,800、食事会 3,500
Act：説明を生成する
```

## 23.2 Reflection の正しい実装方法

財務領域では、LLM の自己評価だけに依存してはいけない。以下を採用する。

> **ルール検証を主とし、LLM Reflection は補助とする。**

### 取引書き込み前の検証

```text
amount > 0
currency が有効
date が妥当
category が有効
merchant の長さが妥当
重複の疑いがあるか
confidence がしきい値未満か
```

### 分析結果の検証

LLM 出力に含まれる数字は Tool Result に由来しなければならない。

Tool Result の例：

```json
{
  "current_month": 78300,
  "previous_month": 68600,
  "difference": 9700
}
```

モデルが以下を生成した場合：

```text
今月は先月より12,000円多く使っています。
```

システムはこの回答を拒否し、再生成しなければならない。

### 推奨する検証方式

```python
def validate_response_numbers(
    response_text: str,
    tool_result: dict,
) -> bool:
    allowed_numbers = extract_numeric_values(tool_result)
    mentioned_numbers = extract_numbers(response_text)
    return mentioned_numbers.issubset(allowed_numbers)
```

追加で検証できる項目：

- 提案が予算の方向性と一致しているか
- 差額の符号が正しいか
- パーセンテージ計算が一致しているか
- カテゴリ合計が総額と一致しているか
- 予測に仮定条件が明示されているか

---

# 24. Expense Agent における RAG の位置づけ

## 24.1 V3 で完全な RAG が不要な理由

Expense Agent の中心データは構造化データである。

```text
金額
日付
カテゴリ
店舗
予算
取引記録
```

ユーザーが質問する：

```text
今月の飲食費はいくら？
```

この場合は SQL を使うべきである。

```sql
SELECT SUM(amount)
FROM transactions
WHERE user_id = :user_id
  AND category = 'food'
  AND transaction_date BETWEEN :start_date AND :end_date;
```

以下のように処理すべきではない：

```text
取引記録を Embedding
↓
ベクトル類似検索
↓
総額を推定
```

ベクトル検索は正確な金額集計に向いていないためである。

結論：

> **すべての金額、予算、統計、予測は SQL または決定論的 Python コードで行う。**

## 24.2 RAG を追加するのに適した場面

### レシートと請求書ドキュメント

- クレジットカード明細 PDF
- Amazon 注文
- 水道光熱費の請求書
- 精算書類
- サブスクリプション契約

ユーザー質問例：

```text
去年、Adobe の請求が含まれていた明細はどれ？
```

### 財務ルール知識ベース

- 会社の精算規定
- 学校の出張規則
- ユーザー定義の予算ルール
- サブスクリプション解約ポリシー
- 財務説明ドキュメント

### 過去の自然言語記憶

ユーザー嗜好を安定して構造化できない場合、非構造化記憶として検索対象にできる。

## 24.3 Agentic RAG の将来フロー

```text
ユーザー質問
↓
Retriever
↓
結果は十分か？
├── いいえ → Query を書き換えて再検索
└── はい → Answer Generator へ渡す
        ↓
資料同士に矛盾がないか確認
        ↓
出典付き回答を生成
```

## 24.4 ベクトルデータベース選定

V3 ではベクトルデータベースを導入しない。

V4 で必要になった場合は、以下を優先する。

```text
PostgreSQL + pgvector
```

理由：

- 構造化取引データとベクトルデータを統一して保存できる。
- デプロイが簡単。
- Pinecone / Milvus を追加運用する必要がない。
- 個人プロジェクトや中小規模データに適している。

---

# 25. マルチ Agent の取捨選択

## 25.1 V3 では CrewAI / AutoGen を採用しない

現時点の Expense Agent では、以下のように人為的に分割する必要はない。

```text
記録 Agent
予算 Agent
予測 Agent
提案 Agent
監督 Agent
```

この分割は以下を引き起こす。

- API コストの増加
- レスポンス遅延の増加
- コンテキスト重複
- デバッグ困難
- 結果の不安定化
- 業務価値を上回るアーキテクチャ複雑度

## 25.2 推奨構造

```text
Expense Agent
├── Transaction Tool
├── Budget Tool
├── Analytics Tool
├── Forecast Tool
├── Anomaly Detection Tool
└── Preference Tool
```

多くの Tool は決定論的コードであり、独立した LLM を必要としない。

## 25.3 将来的に検討できるマルチ Agent 分割

プロダクトが拡張された後は、以下のように分割できる。

```text
Main Finance Agent
├── Expense Agent
├── Receipt Agent
├── Subscription Agent
├── Report Agent
└── Tax / Reimbursement Agent
```

各サブ領域が独立したデータソース、ワークフロー、複雑なタスクを持つ場合のみ、マルチ Agent を使う価値がある。

---

# 26. MCP 互換設計

## 26.1 V3 に MCP は必要か

V3 では、自身の内部関数を MCP 経由で呼び出す必要はない。

内部 Tool は通常の Function Calling のほうが簡単である。

ただし、V4 で MCP Server としてラップできるように、インターフェース層では統一 Tool 定義を残しておくとよい。

## 26.2 将来接続に適した MCP 機能

```text
Gmail MCP
→ 電子レシートを読み取る

Google Drive MCP
→ クレジットカード明細や PDF を読み取る

Filesystem MCP
→ CSV をインポートする

Calendar MCP
→ 旅行、食事会などの支出文脈を識別する

Database MCP
→ 他の AI クライアントが支出分析を問い合わせられるようにする
```

## 26.3 公開可能な MCP Tools

```text
create_transaction
import_bank_csv
get_monthly_summary
get_budget_status
list_large_transactions
forecast_month_end
compare_periods
```

## 26.4 Resources、Tools、Prompts の対応

### Resources

```text
月次支出サマリー
予算情報
取引記録の読み取り専用ビュー
ユーザー嗜好
請求書ファイルのメタデータ
```

### Tools

```text
取引追加
請求書インポート
予算更新
予測生成
週次レポート生成
```

### Prompts

```text
週次財務レビューを生成
今月の支出異常を分析
予算管理提案を生成
今月と先月の差分を説明
```

## 26.5 MCP の安全境界

- デフォルトは読み取り専用。
- 書き込み操作は認証必須。
- 削除操作は二次確認必須。
- 各呼び出しは監査ログに記録する。
- 外部クライアントへデータベース認証情報を公開しない。
- ユーザーデータは `user_id` で厳密に分離する。

---

# 27. 推奨する V3 最終技術スタック

```text
Frontend
React / Next.js

Backend
FastAPI

Agent Orchestration
LangGraph

LLM
Structured Output と Tool Calling をサポートする任意のモデル

Core Data
ローカル開発：SQLite
本番環境：PostgreSQL

Memory
LangGraph Checkpointer
+
PostgreSQL のユーザー嗜好・業務データ

Tools
Python Function Calling

Analytics
SQL + Pandas + 独自 Python

Forecast
決定論的な統計手法

RAG
V3 では使用しない
V4 で請求書、レシート、ルールドキュメントに使用

Vector DB
V3 では使用しない
V4 では pgvector を優先

MCP
V3 では統一 Tool インターフェースを予約
V4 で MCP Server としてラップ

Multi-Agent
V3 では使用しない
```

---

# 28. 技術採用判断表

| 技術 | V3 で採用するか | 役割と理由 |
|---|---:|---|
| LLM API | はい | 意図理解、パラメータ抽出、自然言語説明 |
| Structured Output | はい | フィールド形式を安定させる |
| Function Calling | コア | 取引、予算、分析ツールを安全に呼び出す |
| LangGraph | 推奨 | 状態、分岐、確認、中断復帰 |
| Short-term Memory | はい | 連続会話と指示語解決を支える |
| Long-term Memory | はい | 予算、嗜好、過去取引を保存する |
| Checkpointer | 推奨 | 復帰、確認、デバッグを支える |
| Self-Reflection | はい | ルール検証を主、LLM チェックを補助にする |
| SQL | コア | 金額と統計を正確に処理する |
| RAG | V3 では採用しない | コアデータが構造化取引データであるため |
| Vector DB | V3 では採用しない | 現時点で大規模な非構造化検索が不要 |
| CrewAI / AutoGen | 採用しない | 単一 Agent + 複数 Tool のほうが安定する |
| MCP | 予約 | Gmail、Drive、ファイル、外部クライアントとの将来接続 |
| Web Search | 採用しない | コア機能は公開リアルタイム情報に依存しない |

---

# 29. 最終アーキテクチャ原則

本プロジェクトの最終設計原則：

1. **LLM は理解を担当し、財務上の事実は担当しない。**
2. **SQL と Python が金額、統計、予測を担当する。**
3. **すべての書き込み操作は Schema 検証を通す。**
4. **高リスク操作はユーザー確認を必須とする。**
5. **回答中の数字は Tool Result に由来しなければならない。**
6. **構造化情報はまず SQL に保存し、ベクトルデータベースを濫用しない。**
7. **見栄えのためにマルチ Agent を積み上げず、単一 Agent + 複数 Tool を優先する。**
8. **V3 はコア閉ループを解決し、V4 で RAG、MCP、外部データソースを追加する。**
9. **各 Agent ノードは追跡可能、復旧可能、監査可能であるべき。**
10. **将来 LLM Provider を差し替えても、業務ロジックに影響しない設計にする。**

最終推奨アーキテクチャ：

```text
User
  ↓
React / Next.js
  ↓
FastAPI
  ↓
LangGraph Expense Agent
  ├── Context / Memory
  ├── Intent & Parameter Extraction
  ├── Validator
  ├── Conditional Routing
  ├── Function Calling
  ├── Result Checker
  └── Response Generator
          ↓
Deterministic Tools
  ├── Transaction Service
  ├── Budget Service
  ├── Analytics Service
  ├── Forecast Service
  └── Preference Service
          ↓
SQLite / PostgreSQL
```

この構成により、V3 は以下を同時に満たす。

- 実際の利用可能性
- 財務計算の信頼性
- Agent エンジニアリングとしての完全性
- 履歴書・ポートフォリオでの説明価値
- 将来的に RAG、MCP、マルチ Agent へ拡張できる余地
