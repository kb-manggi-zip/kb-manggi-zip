"""D-day / 통보기한 계산 — compare.ts 의 날짜 로직 이식.

JS 동치 주의:
- new Date('YYYY-MM-DD') 는 UTC 자정으로 파싱된다 → 여기서도 UTC 자정 기준.
- setMonth(m - N) 은 '일(day)'을 유지한 채 월을 이동, 말일 초과 시 다음 달로 롤오버.
  (clamp가 아니라 롤오버) — first-of-month + (day-1)일 로 재현.
- dday = ceil((expiry - now)/day).
"""

import math
from datetime import date, datetime, timedelta, timezone


def parse_date_utc(iso: str) -> datetime:
    """'YYYY-MM-DD'(또는 ISO) → UTC 자정 datetime (JS new Date(iso) 동치)."""
    d = date.fromisoformat(iso[:10])
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def _add_months_rollover(d: date, delta: int) -> date:
    """JS Date.setMonth 롤오버 재현."""
    m = d.month - 1 + delta
    y = d.year + m // 12
    mm = m % 12
    first = date(y, mm + 1, 1)
    return first + timedelta(days=d.day - 1)


def days_between(target: datetime, now: datetime) -> int:
    """ceil((target - now)/1day) — JS Math.ceil(ms/86400000) 동치."""
    return math.ceil((target - now).total_seconds() / 86400)


def d_day(expiry_iso: str, now: datetime) -> int:
    return days_between(parse_date_utc(expiry_iso), now)


def notice_deadline(expiry_iso: str, months: int) -> str:
    """통보기한 날짜(YYYY-MM-DD). expiry - months 개월."""
    expiry = date.fromisoformat(expiry_iso[:10])
    return _add_months_rollover(expiry, -months).isoformat()


def notice_days_left(expiry_iso: str, months: int, now: datetime) -> int:
    deadline = notice_deadline(expiry_iso, months)
    return days_between(parse_date_utc(deadline), now)
