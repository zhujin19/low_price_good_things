from datetime import date, timedelta


def next_target_dates(count: int = 4) -> list[date]:
    today = date.today()
    return [today + timedelta(days=i) for i in range(1, count + 1)]
