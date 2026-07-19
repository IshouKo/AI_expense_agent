import re
from datetime import date, timedelta

from app.schemas import BudgetCreate, TransactionCreate
from app.services.categories import categorize
from app.services.date_utils import current_month, today_jst


AMOUNT_RE = re.compile(r"(\d+(?:,\d{3})*|\d+(?:\.\d+)?)(?:\s*)(万|千|円|日元|yen|jpy)?", re.IGNORECASE)


def parse_amount(text: str) -> int | None:
    for match in AMOUNT_RE.finditer(text):
        raw, unit = match.groups()
        number = float(raw.replace(",", ""))
        if unit == "万":
            number *= 10000
        elif unit == "千":
            number *= 1000
        return int(round(number))
    return None


def parse_date(text: str, base: date | None = None) -> date:
    base_day = base or today_jst()
    if "昨天" in text or "昨日" in text:
        return base_day - timedelta(days=1)
    if "前天" in text:
        return base_day - timedelta(days=2)
    weekdays = {"周一": 0, "星期一": 0, "周二": 1, "星期二": 1, "周三": 2, "星期三": 2, "周四": 3, "星期四": 3, "周五": 4, "星期五": 4, "周六": 5, "星期六": 5, "周日": 6, "星期日": 6, "星期天": 6}
    if "上周" in text:
        for word, weekday in weekdays.items():
            if word in text:
                return base_day - timedelta(days=base_day.weekday() + 7 - weekday)
    return base_day


def infer_type(text: str) -> str:
    if any(word in text for word in ["收入", "工资", "收到", "报销", "入账"]):
        return "income"
    return "expense"


def clean_note(text: str) -> str:
    note = re.sub(AMOUNT_RE, "", text)
    for word in ["今天", "昨天", "前天", "刚刚", "这个月", "花了", "用了", "支付", "收到", "日元", "円"]:
        note = note.replace(word, "")
    return note.strip() or text


def parse_transaction(text: str) -> TransactionCreate | None:
    amount = parse_amount(text)
    if amount is None:
        return None
    category = categorize(text)
    transaction_type = infer_type(text)
    if transaction_type == "income" and category == "other":
        category = "salary" if "工资" in text else "reimbursement" if "报销" in text else "other"
    return TransactionCreate(
        type=transaction_type,
        amount=amount,
        currency="JPY",
        category=category,
        merchant=_infer_merchant(text),
        note=clean_note(text),
        transaction_date=parse_date(text),
        source="agent",
        is_fixed=category in {"housing", "subscription"},
        confidence=0.82 if category != "other" else 0.62,
    )


def parse_budget(text: str) -> BudgetCreate | None:
    amount = parse_amount(text)
    if amount is None or not any(word in text for word in ["预算", "最多", "控制到"]):
        return None
    category = None
    detected_category = categorize(text)
    if detected_category != "other":
        category = detected_category
    return BudgetCreate(month=current_month(), category=category, amount=amount)


def _infer_merchant(text: str) -> str | None:
    match = re.search(r"在([A-Za-z0-9一-龥ぁ-んァ-ンー]+)", text)
    if match:
        return match.group(1)
    if "Amazon" in text or "amazon" in text:
        return "Amazon"
    if "拉面" in text:
        return "拉面店"
    return None
