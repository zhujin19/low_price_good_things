from sqlalchemy.orm import Session

from app.config import settings
from app.models.flight_price import FlightPrice
from app.models.monitor_task import MonitorTask
from app.services.alert_service import create_alert
from app.services.date_service import next_weekday_dates
from app.services.provider_service import ProviderService

provider_service = ProviderService()


def run_check(db: Session, task: MonitorTask) -> int:
    saved_count = 0
    for target_date in next_weekday_dates(task.weekday, settings.target_dates_count):
        rows = provider_service.search_all(
            db,
            task.id,
            task.origin_city,
            task.destination_city,
            target_date,
        )
        for row in rows:
            if not _matches_task(row, task):
                continue
            if _already_saved(db, task.id, target_date, row):
                continue
            flight_price = FlightPrice(task_id=task.id, target_date=target_date, **row)
            db.add(flight_price)
            db.commit()
            db.refresh(flight_price)
            saved_count += 1
            create_alert(
                db,
                task.id,
                flight_price.id,
                f"命中低价: {row['flight_no']} {row['depart_time']} ¥{row['adult_price']}",
            )
    return saved_count


def run_all_enabled_tasks(db: Session):
    for task in db.query(MonitorTask).filter(MonitorTask.enabled.is_(True)).all():
        run_check(db, task)


def _matches_task(row: dict, task: MonitorTask) -> bool:
    if row.get("adult_price", 999999) > task.max_price:
        return False
    depart_time = row.get("depart_time") or ""
    if not depart_time:
        return False
    return _in_time_range(depart_time, task.time_start, task.time_end)


def _already_saved(db: Session, task_id: int, target_date, row: dict) -> bool:
    return (
        db.query(FlightPrice)
        .filter(
            FlightPrice.task_id == task_id,
            FlightPrice.target_date == target_date,
            FlightPrice.provider == row.get("provider"),
            FlightPrice.flight_no == row.get("flight_no"),
            FlightPrice.depart_time == row.get("depart_time"),
            FlightPrice.adult_price == row.get("adult_price"),
        )
        .first()
        is not None
    )


def _in_time_range(value: str, start: str, end: str) -> bool:
    current_minutes = _to_minutes(value)
    start_minutes = _to_minutes(start)
    end_minutes = _to_minutes(end)
    if start_minutes <= end_minutes:
        return start_minutes <= current_minutes <= end_minutes
    return current_minutes >= start_minutes or current_minutes <= end_minutes


def _to_minutes(value: str) -> int:
    hour, minute = value[:5].split(":")
    return int(hour) * 60 + int(minute)
