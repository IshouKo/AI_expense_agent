# AI Expense Agent V3 设计文档

## 1. 项目概述

### 1.1 项目名称

**AI Expense Agent**

### 1.2 V3 目标

V3 不再只是一个“自然语言记账工具”，而是一个能够持续理解用户消费状况、预测预算风险并给出个性化建议的轻量级财务 Agent。

核心目标：

1. 用户可以通过自然语言快速记录支出与收入。
2. 系统自动完成金额、日期、商家、类别和备注解析。
3. 系统支持日、周、月维度的消费统计。
4. 系统能够分析消费变化原因。
5. 系统能够预测月底支出及预算超支风险。
6. 系统能够主动生成可解释的消费建议。
7. 所有关键计算由后端程序完成，LLM 只负责理解、解释和建议，避免模型随意编造数字。

---

## 2. V3 核心能力

### 2.1 自然语言记账

用户输入：

```text
今天午饭吃拉面花了980日元
```

系统解析为：

```json
{
  "type": "expense",
  "amount": 980,
  "currency": "JPY",
  "category": "food",
  "merchant": "拉面店",
  "date": "2026-07-19",
  "note": "午饭吃拉面",
  "confidence": 0.96
}
```

支持输入示例：

```text
昨天坐地铁花了420日元
刚刚在Amazon买书花了3280
这个月房租85000
今天收到实习工资45000
上周五和朋友聚餐花了3600
```

系统需要识别：

- 支出或收入
- 金额
- 币种
- 日期
- 类别
- 商家
- 自然语言备注
- 解析置信度

### 2.2 自动分类

默认类别：

| 类别代码 | 显示名称 | 示例 |
|---|---|---|
| food | 餐饮 | 拉面、咖啡、外卖 |
| transport | 交通 | 地铁、公交、出租车 |
| shopping | 购物 | Amazon、衣服、电子产品 |
| housing | 居住 | 房租、水电、家具 |
| entertainment | 娱乐 | 电影、游戏、聚会 |
| education | 学习 | 书籍、课程、学会注册 |
| health | 健康 | 药品、医院、健身房 |
| subscription | 订阅 | ChatGPT、Netflix、云服务 |
| travel | 旅行 | 酒店、机票、签证 |
| social | 社交 | 聚餐、礼物 |
| salary | 工资收入 | 实习工资、兼职工资 |
| reimbursement | 报销 | 公司报销、学校报销 |
| other | 其他 | 无法归类的交易 |

分类优先级：

1. 用户明确指定分类。
2. 商家规则匹配。
3. 关键词规则匹配。
4. LLM 分类。
5. 无法判断时归入 `other`。

### 2.3 消费统计

支持以下查询：

```text
我今天花了多少钱？
这个月餐饮花了多少？
本周最大的三笔支出是什么？
这个月收入和支出分别是多少？
最近30天每天平均花多少？
```

系统输出必须来自数据库计算结果，而不是由 LLM 自行计算。

### 2.4 消费变化分析

用户可以询问：

```text
为什么这个月比上个月花得多？
最近餐饮支出为什么上涨？
这个月哪一类支出增长最快？
```

后端首先计算：

- 当前周期总支出
- 对比周期总支出
- 各类别差额
- 各类别增长率
- 大额交易数量
- 新增商家或新增订阅
- 交易频率变化

然后将结构化分析结果发送给 LLM，生成自然语言解释。

示例输出：

```text
你本月目前比上个月同期多支出 12,400 日元，主要来自三部分：

1. 购物支出增加 6,800 日元，主要是一次 Amazon 购书。
2. 餐饮支出增加 3,900 日元，外食次数从 8 次增加到 13 次。
3. 本月新增了一笔 1,700 日元的订阅支出。

其中购物是本月增长最大的类别。
```

### 2.5 预算管理

用户可以设置：

- 月度总预算
- 各类别预算
- 固定支出
- 储蓄目标

示例：

```text
这个月总预算设置为12万日元
餐饮预算设成3万
购物最多1万5
每个月至少存5万
```

预算表：

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

### 2.6 月底支出预测

系统根据当前月份已过去天数和消费数据预测月底支出。

基础预测：

```text
预计月底支出 = 当前累计支出 / 已过去天数 × 当月总天数
```

改进预测：

```text
预计月底支出 = 固定支出 + 可变支出日均值 × 剩余天数
```

其中：

- 固定支出：房租、订阅、固定账单等。
- 可变支出：餐饮、购物、娱乐、交通等。
- 日均值可以采用最近 7 天、14 天或本月均值。
- 数据不足时降级到基础预测。

预测输出：

```json
{
  "current_spending": 78000,
  "predicted_month_end_spending": 132500,
  "monthly_budget": 120000,
  "predicted_over_budget": 12500,
  "risk_level": "high"
}
```

风险等级：

| 等级 | 条件 |
|---|---|
| low | 预计支出低于预算 85% |
| medium | 预计支出达到预算 85% 至 100% |
| high | 预计支出超过预算 |
| critical | 预计超预算超过 15% |

### 2.7 智能建议

Agent 的建议必须基于真实数据。

示例：

```text
按照当前速度，你月底可能超预算约12,500日元。

最容易调整的是餐饮和购物：
- 本月剩余12天，建议将每日可变支出控制在2,300日元以内。
- 餐饮预算还剩6,400日元，平均每天约533日元。
- 本月已有两笔非必要购物，合计8,200日元。
```

建议类型：

- 预算预警
- 类别超支提醒
- 大额消费提示
- 重复订阅提示
- 支出频率异常
- 月底余额预测
- 储蓄目标风险
- 每日可用预算建议

### 2.8 主动提醒

V3 可以先实现“进入 App 时生成提醒”，不必做复杂的后台推送。

提醒触发条件：

- 某类别使用超过预算 80%
- 总预算使用超过 80%
- 预计月底超预算
- 单笔支出超过自定义阈值
- 连续多天高消费
- 订阅即将扣款
- 本周消费显著高于过去四周均值

示例：

```text
预算提醒：你的餐饮预算已使用 87%，本月还剩 12 天。
```

---

## 3. 产品范围

### 3.1 V3 必做功能

- 自然语言新增支出和收入
- 手动新增、修改和删除交易
- 自动分类
- 日、周、月统计
- 分类图表
- 月度预算设置
- 类别预算设置
- 本月与上月对比
- 月底支出预测
- 超预算风险评估
- AI 消费分析
- AI 节省建议
- 数据导出 CSV

### 3.2 V3 暂不实现

- 银行账户直连
- 信用卡 API 自动同步
- Apple Wallet 自动读取
- 自动支付
- 股票投资建议
- 税务申报
- 多人共享账本
- 多币种实时汇率
- 完全自动后台推送

这些功能成本和合规复杂度较高，放到 V4 或以后。

---

## 4. 用户场景

### 场景一：快速记账

用户：

```text
今天晚饭和朋友吃烤肉花了4200日元
```

Agent：

```text
已记录：
- 金额：4,200日元
- 类别：社交
- 日期：2026年7月19日
- 备注：和朋友吃烤肉
```

### 场景二：查询本月消费

用户：

```text
这个月我花了多少？
```

Agent：

```text
本月目前共支出 78,300 日元，主要类别为：
- 居住：40,000日元
- 餐饮：18,600日元
- 交通：7,800日元
- 购物：6,900日元
```

### 场景三：分析消费增加原因

用户：

```text
为什么这个月支出比上个月高？
```

Agent：

```text
你本月目前比上个月同期多支出 9,700 日元。
主要原因是购物增加 5,200 日元、餐饮增加 3,100 日元。
购物增长主要来自一笔 Amazon 购书和一笔电子产品支出。
```

### 场景四：预算预测

用户：

```text
我这个月会超预算吗？
```

Agent：

```text
按照当前消费速度，预计月底总支出约为 132,500 日元。
你的预算是 120,000 日元，预计超出约 12,500 日元，风险等级为高。
```

### 场景五：节省建议

用户：

```text
怎么控制到12万以内？
```

Agent：

```text
本月还剩12天，要控制在12万以内，剩余可支出约41,700日元。
建议：
1. 将每日可变支出控制在2,300日元以内。
2. 暂停非必要购物，预计可减少约8,000日元。
3. 餐饮预算剩余6,400日元，建议减少外食次数。
```

---

## 5. 系统架构

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

### 5.1 设计原则

1. **数据库是事实来源。**
2. **金额计算由 Python 完成。**
3. **LLM 不直接修改数据库。**
4. **LLM 只能通过受控 Tool Calling 执行操作。**
5. **所有写操作保留日志。**
6. **低置信度解析需要用户确认。**

---

## 6. Agent 工作流程

### 6.1 意图识别

用户输入首先分类为：

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
用户输入
  ↓
识别意图
  ↓
抽取参数
  ↓
参数验证
  ↓
选择工具
  ↓
执行数据库或分析函数
  ↓
检查结果
  ↓
生成自然语言回复
```

### 6.3 Tool 定义

#### add_transaction

```json
{
  "type": "expense",
  "amount": 980,
  "currency": "JPY",
  "category": "food",
  "merchant": "一兰",
  "transaction_date": "2026-07-19",
  "note": "午饭"
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

输入必须包含后端计算后的结构化结果：

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

## 7. 数据库设计

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

金额建议以最小货币单位整数保存，JPY 可直接使用整数。

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

`category = NULL` 表示月度总预算。

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

## 8. API 设计

### 8.1 Agent 对话

```http
POST /api/v1/agent/chat
```

请求：

```json
{
  "message": "今天午饭花了980日元"
}
```

响应：

```json
{
  "intent": "ADD_TRANSACTION",
  "message": "已记录今天的午饭支出980日元。",
  "data": {
    "transaction_id": 101,
    "amount": 980,
    "category": "food"
  }
}
```

### 8.2 交易管理

```http
GET    /api/v1/transactions
POST   /api/v1/transactions
PATCH  /api/v1/transactions/{id}
DELETE /api/v1/transactions/{id}
```

### 8.3 消费统计

```http
GET /api/v1/analytics/summary
GET /api/v1/analytics/categories
GET /api/v1/analytics/trend
GET /api/v1/analytics/compare
GET /api/v1/analytics/top-transactions
```

### 8.4 预算管理

```http
GET  /api/v1/budgets/{month}
POST /api/v1/budgets
PUT  /api/v1/budgets/{id}
```

### 8.5 预测与建议

```http
GET  /api/v1/forecast/{month}
POST /api/v1/advice/generate
GET  /api/v1/alerts
```

### 8.6 数据导出

```http
GET /api/v1/export/csv
```

---

## 9. 页面设计

### 9.1 Dashboard

显示：

- 本月总支出
- 本月总收入
- 预算剩余
- 预计月底支出
- 超预算风险
- 分类占比图
- 每日消费趋势
- 最近交易
- Agent 提醒

### 9.2 Chat 页面

支持自然语言输入：

```text
今天咖啡480
这个月花了多少
为什么比上个月贵
帮我把餐饮预算改成3万
```

### 9.3 Transactions 页面

支持：

- 查看交易
- 搜索
- 按日期筛选
- 按类别筛选
- 修改
- 删除
- CSV 导出

### 9.4 Budget 页面

显示：

- 总预算
- 各类别预算
- 已使用金额
- 使用比例
- 剩余预算
- 预计月底金额

### 9.5 Insights 页面

显示：

- 本月与上月对比
- 增长最快类别
- 主要消费变化原因
- 大额支出
- 异常消费
- AI 建议

---

## 10. 预测算法

### 10.1 基础版本

```python
predicted = current_spending / elapsed_days * total_days
```

### 10.2 推荐版本

```python
predicted = fixed_costs + average_variable_daily_spending * remaining_days + current_variable_spending
```

建议规则：

1. 识别当月固定支出。
2. 计算最近 14 天可变支出的日均值。
3. 若数据少于 7 天，则使用本月日均值。
4. 对极端大额支出做截尾处理，避免一次购买严重扭曲预测。
5. 同时返回乐观、中性、悲观区间。

示例：

```json
{
  "optimistic": 118000,
  "expected": 132500,
  "pessimistic": 145000
}
```

---

## 11. AI 提示词设计

### 11.1 交易解析 Prompt

```text
你是一个个人记账系统的交易解析器。
请从用户输入中提取交易信息，并严格返回 JSON。

规则：
1. 不允许虚构金额。
2. 没有币种时默认 JPY。
3. 根据用户时区 Asia/Tokyo 解析“今天、昨天、上周五”等日期。
4. 无法确定类别时返回 other。
5. 无法确定关键字段时列入 missing_fields。
6. 不执行任何数据库操作。
```

### 11.2 消费建议 Prompt

```text
你是一个个人消费分析助手。
所有数字均来自后端计算，不得修改、重新计算或虚构。
请根据预算、预测、类别变化和交易频率生成简洁、可执行的建议。

要求：
1. 明确指出最重要的1至3个原因。
2. 给出可执行建议。
3. 不提供股票、投资或贷款建议。
4. 不使用羞辱、责备或过度焦虑的语气。
5. 明确区分事实、预测和建议。
```

---

## 12. 安全与可靠性

### 12.1 数据安全

- 默认本地 SQLite。
- 不保存银行卡密码。
- 不保存完整信用卡号。
- API Key 存放在环境变量。
- 日志中隐藏敏感信息。
- 导出文件需要用户主动触发。

### 12.2 LLM 安全

- 使用 JSON Schema 或 Structured Outputs。
- Tool 参数必须经过 Pydantic 验证。
- 删除交易前需要二次确认。
- 大额异常解析需要确认。
- Agent 不得直接执行 SQL。
- 所有数据库操作封装成固定工具。

### 12.3 财务免责声明

该系统仅用于个人消费记录和预算辅助，不构成投资、税务、法律或专业财务建议。

---

## 13. 推荐技术栈

### 后端

- Python 3.12
- FastAPI
- SQLAlchemy 2.0
- Pydantic
- SQLite
- Alembic

### Agent

- OpenAI API 或 Gemini API
- Function Calling / Structured Outputs
- 自定义轻量 Agent Orchestrator

第一版不需要 LangGraph、CrewAI 或复杂多 Agent 框架。

### 前端

最省时间方案：

- Streamlit

作品集强化方案：

- Next.js
- TypeScript
- Tailwind CSS
- ECharts 或 Recharts

### 测试

- pytest
- FastAPI TestClient

### 部署

低成本方案：

- 前端：Vercel
- 后端：Render / Railway
- 数据库：SQLite 单机或 Supabase PostgreSQL

---

## 14. 项目目录建议

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

## 15. 开发顺序

### Phase 1：基础数据层

- 创建 FastAPI 项目
- 创建 SQLite 数据库
- 实现 Transaction CRUD
- 实现 Budget CRUD
- 创建测试数据

### Phase 2：自然语言记账

- 实现交易解析 Prompt
- 使用 Structured Outputs
- 实现 `add_transaction` Tool
- 实现低置信度确认流程

### Phase 3：统计分析

- 日、周、月统计
- 分类统计
- 趋势统计
- 当前周期与上周期对比
- 大额交易分析

### Phase 4：预算与预测

- 总预算和类别预算
- 固定支出识别
- 月底支出预测
- 风险等级计算
- 每日可用预算计算

### Phase 5：AI Insights

- 消费增加原因总结
- 超预算原因总结
- 个性化节省建议
- 主动提醒生成

### Phase 6：前端与部署

- Dashboard
- Chat
- Transactions
- Budget
- Insights
- CSV 导出
- 部署

---

## 16. 验收标准

### 自然语言解析

- 常见中文记账语句解析成功率达到 90% 以上。
- 金额不得出现模型编造。
- 相对日期能够正确转换为具体日期。

### 统计

- 所有统计结果与数据库 SQL 结果一致。
- 日、周、月筛选准确。
- 分类总和等于总支出。

### 预算预测

- 能返回当前支出、预计支出、预算差额和风险等级。
- 数据不足时明确提示预测可信度较低。

### AI 建议

- 建议中的数字全部可追溯到后端结果。
- 至少给出一个具体、可执行建议。
- 不生成投资或贷款建议。

### 稳定性

- LLM API 失败时不影响已有记账数据。
- 重复提交需要防止重复记账。
- 删除操作需要确认。

---

## 17. 简历描述示例

```text
Developed an AI-powered expense management agent using FastAPI, SQLite and LLM function calling. The system supports natural-language transaction entry, automatic categorization, budget tracking, month-end spending forecasting, period-over-period analysis and explainable personalized spending recommendations. All financial calculations are performed by deterministic backend tools, while the LLM is restricted to intent understanding and natural-language explanation.
```

日文版：

```text
FastAPI、SQLite、LLM Function Callingを用いたAI家計管理Agentを開発。自然言語による支出登録、自動カテゴリ分類、予算管理、月末支出予測、前月比較、支出増加要因の分析および説明可能な節約提案を実装した。金額計算はすべてバックエンド側で決定論的に処理し、LLMは意図理解と自然言語説明に限定することで信頼性を確保した。
```

---

## 18. 最终 MVP 定义

V3 完成时，用户应该能够完成以下完整流程：

```text
“今天午饭980日元”
        ↓
自动记录并分类
        ↓
“这个月花了多少？”
        ↓
返回真实统计
        ↓
“为什么比上个月多？”
        ↓
解释主要增长类别和交易
        ↓
“月底会超预算吗？”
        ↓
生成预测和风险等级
        ↓
“怎么控制在12万以内？”
        ↓
给出基于数据的可执行建议
```

这就是 V3 的核心闭环：

> **记录 → 统计 → 对比 → 预测 → 建议。**

---

# 19. 通用 AI Agent 技术体系与本项目的对应关系

本节说明本项目与通用 AI Agent 技术体系之间的关系，并明确哪些技术在 V3 中采用、哪些暂不采用，以及对应的工程理由。

## 19.1 总体结论

本项目并不是把所有 Agent 相关技术全部堆叠起来，而是以 Expense Agent 的业务目标为中心进行取舍。

V3 的核心原则是：

> **一个主 Agent + 多个确定性的 Python / SQL Tools。**

其中：

- LLM 负责理解用户意图、抽取参数、选择工具以及生成自然语言解释；
- 后端工具负责金额计算、预算判断、趋势分析、预测和数据库写入；
- 数据库保存交易、预算、偏好和历史状态；
- Agent 编排层负责状态管理、条件分支、确认、错误恢复和中断续执行。

因此，V3 重点采用：

- LLM API；
- Structured Output；
- Function Calling / Tool Use；
- LangGraph；
- Short-term Memory；
- Long-term Memory；
- Checkpointer；
- 规则校验与轻量 Self-Reflection；
- SQL / Python 驱动的确定性分析。

V3 暂不强制采用：

- 完整 RAG；
- 向量数据库；
- CrewAI / AutoGen 多 Agent；
- MCP Server。

这些能力可以在 V4 以后按需加入。

---

## 19.2 LLM API 与模型抽象

### 19.2.1 LLM 在本项目中的职责

LLM 只负责以下任务：

1. 意图分类；
2. 交易字段抽取；
3. 工具选择；
4. 追问缺失信息；
5. 基于工具返回结果生成自然语言说明；
6. 对用户请求进行多步任务拆解。

LLM 不负责：

- 直接计算月度总支出；
- 自行推测数据库中的金额；
- 直接生成预算结论；
- 无工具依据地判断是否超支；
- 绕过后端直接修改数据库。

### 19.2.2 Provider 抽象

不要把特定模型名称写死在业务代码中。建议定义统一接口：

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

配置示例：

```yaml
llm:
  provider: openai
  model: ${LLM_MODEL}
  temperature: 0
  max_retries: 2
  timeout_seconds: 30
```

这样可以在不修改业务逻辑的情况下替换模型供应商。

### 19.2.3 运维注意事项

需要考虑：

- Token 消耗监控；
- Rate Limit 重试；
- 指数退避；
- 超时处理；
- 上下文窗口裁剪；
- 历史消息摘要；
- 请求日志；
- 模型失败后的降级策略。

建议记录以下指标：

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

# 20. LangGraph 架构设计

## 20.1 为什么在 V3 中采用 LangGraph

V3 并非必须依赖 LangGraph，纯 Python 状态机也能实现。但如果项目目标还包括：

- 学习 Agent 工程；
- 展示状态管理能力；
- 支持中断恢复；
- 支持 Human-in-the-loop；
- 支持多步工具调用；
- 支持条件分支和错误恢复；

则 LangGraph 很适合本项目。

## 20.2 四个核心概念在本项目中的映射

### State

State 是整个 Agent 工作流中流动的数据。

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

建议包含以下节点：

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

普通边表示固定流程：

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

条件边根据状态决定下一步：

```python
def route_after_validation(state: ExpenseAgentState) -> str:
    if state.get("validation_errors"):
        return "request_clarification"

    if state.get("requires_confirmation"):
        return "request_confirmation"

    return "execute_tool"
```

## 20.3 推荐工作流

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
  ├── 缺少参数 → Clarification
  ├── 高风险操作 → Confirmation
  ├── 普通查询 → Query Tool
  ├── 交易写入 → Transaction Tool
  ├── 预算操作 → Budget Tool
  ├── 趋势分析 → Analytics Tool
  └── 月末预测 → Forecast Tool
          ↓
Result Checker
  ├── 数据不足 → Clarification
  ├── 工具失败 → Error Recovery
  ├── 结果异常 → Re-evaluate
  └── 正常 → Response Generator
                      ↓
                  Save Memory
                      ↓
                     END
```

## 20.4 LangGraph 伪代码

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

# 21. Function Calling / Tool Use 设计

## 21.1 基本流程

```text
1. 开发者定义 Tool Schema
2. LLM 判断调用哪个 Tool
3. 后端验证参数
4. 后端执行真实函数
5. Tool Result 返回 Agent
6. Agent 根据结果生成回复
```

## 21.2 示例：设置预算

用户输入：

```text
这个月餐饮预算设置为3万日元
```

LLM 生成工具调用：

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

后端执行：

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

最终回复：

```text
已将 2026 年 7 月的餐饮预算设置为 30,000 日元。
```

## 21.3 推荐 Tools

### 交易类

```text
create_transaction
update_transaction
delete_transaction
list_transactions
find_possible_duplicates
```

### 预算类

```text
set_budget
get_budget_status
list_budgets
update_budget
```

### 分析类

```text
get_period_summary
compare_periods
get_category_breakdown
get_large_transactions
get_spending_trend
```

### 预测类

```text
forecast_month_end
estimate_remaining_budget
calculate_safe_daily_spending
```

### 用户偏好类

```text
set_user_preference
get_user_preferences
set_merchant_category_rule
```

## 21.4 安全规则

以下操作必须经过确认：

- 删除交易；
- 批量修改交易；
- 批量导入覆盖；
- 修改历史月份预算；
- 清空用户数据；
- 导出完整财务记录。

原则：

> LLM 只能提出工具调用请求，不能绕过后端校验直接执行高风险操作。

---

# 22. Memory Management

## 22.1 短期记忆

短期记忆用于维持当前会话上下文。

例：

```text
用户：这个月餐饮花了多少？
Agent：18,600 日元。
用户：那上个月呢？
```

系统需要知道：

```text
“那” = 餐饮支出
比较期间 = 上个月
```

建议在 State 中保存：

```python
current_topic = "food spending"
current_period = "2026-07"
previous_intent = "QUERY_CATEGORY_SPENDING"
```

实现方式：

- 最近 N 轮消息窗口；
- 当前会话 State；
- 超长会话摘要；
- LangGraph Checkpointer。

## 22.2 长期记忆

长期记忆分为两类。

### 结构化业务记忆

保存在 SQL 数据库：

```text
用户默认货币
用户时区
预算
交易
储蓄目标
固定支出
商家分类规则
提醒阈值
```

这类信息不应使用向量数据库替代。

### 非结构化偏好记忆

例如：

```text
和朋友一起吃饭算作社交，不算普通餐饮。
金额低于 1,000 日元时不要频繁提醒。
回答尽量简洁。
每月 25 日是工资日。
```

建议优先结构化保存：

```json
{
  "preference_key": "meal_with_friends_category",
  "preference_value": "social"
}
```

只有当偏好数量很大且难以结构化时，才考虑向量检索。

## 22.3 建议的数据表

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

Checkpointer 用于保存每个节点运行后的 State 快照。

可实现：

- 中断恢复；
- Human-in-the-loop；
- 错误后重试；
- 从确认节点继续；
- 调试历史状态；
- 查看 Agent 的执行轨迹。

推荐生产环境使用数据库型 Checkpointer，本地开发可先使用内存或 SQLite。

## 22.5 Summarization Memory

当对话过长时：

```text
完整历史消息
↓
摘要节点
↓
保留重要事实、未完成任务、用户偏好
↓
删除冗余历史
```

摘要内容应包含：

- 当前讨论主题；
- 已确认事实；
- 未完成操作；
- 重要用户偏好；
- 最近一次工具结果；
- 待确认风险操作。

---

# 23. Planning、Reasoning 与 Self-Reflection

## 23.1 ReAct 在本项目中的应用

用户问：

```text
为什么这个月比上个月花得多？
```

Agent 应执行：

```text
Reason：需要比较两个自然月
Act：调用 compare_periods
Observe：本月多支出 9,700 日元
Reason：需要知道主要增长类别
Act：调用 get_category_breakdown
Observe：购物 +6,800，聚餐 +3,500
Reason：需要找到代表性交易
Act：调用 get_large_transactions
Observe：Amazon 6,800，聚餐 3,500
Act：生成解释
```

## 23.2 Reflection 的正确实现方式

财务场景不能只依赖 LLM 自我评价。应采用：

> **规则校验为主，LLM Reflection 为辅。**

### 交易写入前校验

```text
amount > 0
currency 合法
date 合理
category 合法
merchant 长度合理
是否疑似重复
confidence 是否低于阈值
```

### 分析结果校验

LLM 输出中出现的数字必须来自 Tool Result。

例如 Tool Result：

```json
{
  "current_month": 78300,
  "previous_month": 68600,
  "difference": 9700
}
```

如果模型生成：

```text
本月比上月多花了 12,000 日元。
```

系统必须拒绝该回答并重新生成。

### 推荐校验方式

```python
def validate_response_numbers(
    response_text: str,
    tool_result: dict,
) -> bool:
    allowed_numbers = extract_numeric_values(tool_result)
    mentioned_numbers = extract_numbers(response_text)
    return mentioned_numbers.issubset(allowed_numbers)
```

还可以校验：

- 建议是否与预算方向一致；
- 差额符号是否正确；
- 百分比计算是否一致；
- 分类合计是否等于总额；
- 预测是否标明假设条件。

---

# 24. RAG 在 Expense Agent 中的定位

## 24.1 V3 为什么不需要完整 RAG

Expense Agent 的核心数据是结构化数据：

```text
金额
日期
类别
商家
预算
交易记录
```

用户问：

```text
这个月餐饮花了多少？
```

应该使用 SQL：

```sql
SELECT SUM(amount)
FROM transactions
WHERE user_id = :user_id
  AND category = 'food'
  AND transaction_date BETWEEN :start_date AND :end_date;
```

不应该：

```text
交易记录 Embedding
↓
向量相似度搜索
↓
估算总金额
```

因为向量检索不适合精确金额聚合。

结论：

> **所有金额、预算、统计、预测均由 SQL 或确定性 Python 代码完成。**

## 24.2 适合加入 RAG 的场景

### 收据与账单文档

- 信用卡账单 PDF；
- Amazon 订单；
- 水电费账单；
- 报销文件；
- 订阅合同。

用户可询问：

```text
去年哪一份账单里出现过 Adobe 扣费？
```

### 财务规则知识库

- 公司报销规定；
- 学校差旅规则；
- 用户自定义预算规则；
- 订阅取消政策；
- 财务说明文档。

### 历史自然语言记忆

当用户偏好无法稳定结构化时，可将其作为非结构化记忆做检索。

## 24.3 Agentic RAG 的未来流程

```text
用户问题
↓
Retriever
↓
结果充分？
├── 否 → 改写 Query 并重新检索
└── 是 → 交给 Answer Generator
        ↓
检查资料是否矛盾
        ↓
生成带来源回答
```

## 24.4 向量数据库选择

V3 不引入向量数据库。

V4 如需加入，优先考虑：

```text
PostgreSQL + pgvector
```

原因：

- 结构化交易和向量数据统一存储；
- 部署简单；
- 不需要额外维护 Pinecone / Milvus；
- 适合个人项目和中小规模数据。

---

# 25. 多 Agent 的取舍

## 25.1 V3 不采用 CrewAI / AutoGen

Expense Agent 目前不需要人为拆分成：

```text
记账 Agent
预算 Agent
预测 Agent
建议 Agent
监督 Agent
```

这样会造成：

- API 成本增加；
- 响应延迟增加；
- 上下文重复；
- 调试困难；
- 结果不稳定；
- 架构复杂度高于业务价值。

## 25.2 推荐结构

```text
Expense Agent
├── Transaction Tool
├── Budget Tool
├── Analytics Tool
├── Forecast Tool
├── Anomaly Detection Tool
└── Preference Tool
```

多数 Tool 应为确定性代码，不需要独立 LLM。

## 25.3 未来可考虑的多 Agent 拆分

当产品扩展后，可以拆分为：

```text
Main Finance Agent
├── Expense Agent
├── Receipt Agent
├── Subscription Agent
├── Report Agent
└── Tax / Reimbursement Agent
```

仅当各子领域拥有独立数据源、工作流和复杂任务时，才值得使用多 Agent。

---

# 26. MCP 兼容设计

## 26.1 V3 是否需要 MCP

V3 不需要通过 MCP 调用自己的内部函数。

内部 Tool 使用普通 Function Calling 更简单。

但可以在接口层预留统一 Tool 定义，以便 V4 封装为 MCP Server。

## 26.2 未来适合接入的 MCP 能力

```text
Gmail MCP
→ 读取电子收据

Google Drive MCP
→ 读取信用卡账单和 PDF

Filesystem MCP
→ 导入 CSV

Calendar MCP
→ 识别旅行、聚餐等消费上下文

Database MCP
→ 供其他 AI 客户端查询消费分析
```

## 26.3 可暴露的 MCP Tools

```text
create_transaction
import_bank_csv
get_monthly_summary
get_budget_status
list_large_transactions
forecast_month_end
compare_periods
```

## 26.4 Resources、Tools、Prompts 的映射

### Resources

```text
月度消费摘要
预算信息
交易记录只读视图
用户偏好
账单文件元数据
```

### Tools

```text
新增交易
导入账单
更新预算
生成预测
生成周报
```

### Prompts

```text
生成每周财务回顾
分析本月支出异常
生成预算控制建议
解释本月与上月差异
```

## 26.5 MCP 安全边界

- 默认只读；
- 写操作必须鉴权；
- 删除操作必须二次确认；
- 每次调用记录审计日志；
- 不向外部客户端暴露数据库凭据；
- 用户数据按 user_id 严格隔离。

---

# 27. 推荐的 V3 最终技术栈

```text
Frontend
React / Next.js

Backend
FastAPI

Agent Orchestration
LangGraph

LLM
任意支持 Structured Output 与 Tool Calling 的模型

Core Data
本地开发：SQLite
生产环境：PostgreSQL

Memory
LangGraph Checkpointer
+
PostgreSQL 用户偏好与业务数据

Tools
Python Function Calling

Analytics
SQL + Pandas + 自定义 Python

Forecast
确定性统计方法

RAG
V3 不使用
V4 用于账单、收据、规则文档

Vector DB
V3 不使用
V4 优先 pgvector

MCP
V3 预留统一 Tool 接口
V4 封装 MCP Server

Multi-Agent
V3 不使用
```

---

# 28. 技术采用决策表

| 技术 | V3 是否采用 | 作用与理由 |
|---|---:|---|
| LLM API | 是 | 意图理解、参数抽取、自然语言解释 |
| Structured Output | 是 | 确保字段格式稳定 |
| Function Calling | 核心 | 安全调用交易、预算、分析工具 |
| LangGraph | 推荐 | 状态、分支、确认、中断恢复 |
| Short-term Memory | 是 | 支持连续对话与指代解析 |
| Long-term Memory | 是 | 保存预算、偏好、历史交易 |
| Checkpointer | 推荐 | 支持恢复、确认和调试 |
| Self-Reflection | 是 | 规则校验为主，LLM 检查为辅 |
| SQL | 核心 | 精确处理金额与统计 |
| RAG | V3 不采用 | 核心数据为结构化交易数据 |
| Vector DB | V3 不采用 | 当前没有大规模非结构化检索需求 |
| CrewAI / AutoGen | 不采用 | 单 Agent + 多 Tool 更稳定 |
| MCP | 预留 | 后续连接 Gmail、Drive、文件和外部客户端 |
| Web Search | 不采用 | 核心功能不依赖公开实时信息 |

---

# 29. 最终架构原则

本项目的最终设计原则如下：

1. **LLM 负责理解，不负责财务事实。**
2. **SQL 和 Python 负责金额、统计和预测。**
3. **所有写操作必须经过 Schema 校验。**
4. **高风险操作必须要求用户确认。**
5. **回复中的数字必须来源于 Tool Result。**
6. **结构化信息优先存 SQL，不滥用向量数据库。**
7. **优先单 Agent + 多 Tool，不为了展示而堆叠多 Agent。**
8. **V3 解决核心闭环，V4 再加入 RAG、MCP 和外部数据源。**
9. **每个 Agent 节点都应可追踪、可恢复、可审计。**
10. **系统应支持未来替换 LLM Provider，而不影响业务逻辑。**

最终推荐架构：

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

这使 V3 同时具备：

- 实际可用性；
- 财务计算可靠性；
- Agent 工程完整性；
- 简历展示价值；
- 后续扩展 RAG、MCP 和多 Agent 的空间。
