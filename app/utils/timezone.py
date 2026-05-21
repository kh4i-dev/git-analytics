from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
UTC = ZoneInfo("UTC")

SHORT_FMT = "%d/%m/%Y %H:%M"
DATE_FMT = "%d/%m/%Y"
TIME_FMT = "%H:%M"
FULL_FMT = "%H:%M • %d/%m/%Y"
LOG_FMT = "%d/%m/%Y %H:%M:%S"
TABLE_FMT = "%H:%M • %d/%m"


def utc_to_vn(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(VN_TZ)


def now_vn() -> datetime:
    return datetime.now(VN_TZ)


def now_utc() -> datetime:
    return datetime.now(UTC)


def format_vn(dt: datetime | None, fmt: str = SHORT_FMT) -> str:
    if dt is None:
        return "—"
    vn_dt = utc_to_vn(dt)
    return vn_dt.strftime(fmt)


def format_date(dt: datetime | None) -> str:
    return format_vn(dt, DATE_FMT)


def format_time(dt: datetime | None) -> str:
    return format_vn(dt, TIME_FMT)


def format_full(dt: datetime | None) -> str:
    return format_vn(dt, FULL_FMT)


def format_table(dt: datetime | None) -> str:
    return format_vn(dt, TABLE_FMT)


def format_compact(dt: datetime | None) -> str:
    return format_vn(dt, FULL_FMT)


def isoformat_vn(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    vn_dt = utc_to_vn(dt)
    return vn_dt.isoformat()


def relative_time(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    vn_dt = utc_to_vn(dt)
    now = now_vn()
    diff = now - vn_dt

    if diff < timedelta(minutes=1):
        return "vừa xong"
    if diff < timedelta(hours=1):
        m = int(diff.total_seconds() // 60)
        return f"{m} phút trước"
    if diff < timedelta(days=1):
        h = int(diff.total_seconds() // 3600)
        return f"{h} giờ trước"
    if diff < timedelta(days=2):
        return "hôm qua"
    if diff < timedelta(days=30):
        d = diff.days
        return f"{d} ngày trước"
    if diff < timedelta(days=365):
        m = diff.days // 30
        return f"{m} tháng trước"
    return format_date(vn_dt)


def is_stale_sync(dt: datetime | None, threshold_minutes: int = 15) -> bool:
    if dt is None:
        return False
    vn_dt = utc_to_vn(dt)
    now = now_vn()
    return now - vn_dt > timedelta(minutes=threshold_minutes)
