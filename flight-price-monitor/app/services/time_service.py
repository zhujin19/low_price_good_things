from datetime import date, datetime
from zoneinfo import ZoneInfo

BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def beijing_now() -> datetime:
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)


def beijing_today() -> date:
    return datetime.now(BEIJING_TZ).date()


def format_beijing(value: datetime | None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if value is None:
        return ""
    if value.tzinfo is not None:
        value = value.astimezone(BEIJING_TZ).replace(tzinfo=None)
    return value.strftime(fmt)
