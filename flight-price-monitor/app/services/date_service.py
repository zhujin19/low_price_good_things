from datetime import date, timedelta

from app.services.time_service import beijing_today


def next_weekday_dates(weekday: int, count: int = 4) -> list[date]:
    if weekday < 0 or weekday > 6:
        raise ValueError("weekday must be 0-6")

    today = beijing_today()
    days_until = (weekday - today.weekday()) % 7
    if days_until == 0:
        days_until = 7
    first = today + timedelta(days=days_until)
    return [first + timedelta(days=7 * i) for i in range(count)]
