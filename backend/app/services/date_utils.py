from calendar import monthrange
from datetime import date, timedelta


def today_jst() -> date:
    return date.today()


def month_bounds(month: str) -> tuple[date, date]:
    year, month_num = [int(part) for part in month.split("-")]
    last_day = monthrange(year, month_num)[1]
    return date(year, month_num, 1), date(year, month_num, last_day)


def current_month() -> str:
    return today_jst().strftime("%Y-%m")


def week_bounds(day: date | None = None) -> tuple[date, date]:
    target = day or today_jst()
    start = target - timedelta(days=target.weekday())
    return start, start + timedelta(days=6)


def previous_month_same_span(current_start: date, current_end: date) -> tuple[date, date]:
    year = current_start.year
    month = current_start.month - 1
    if month == 0:
        year -= 1
        month = 12
    last_day = monthrange(year, month)[1]
    start = date(year, month, 1)
    span_day = min(current_end.day, last_day)
    return start, date(year, month, span_day)
