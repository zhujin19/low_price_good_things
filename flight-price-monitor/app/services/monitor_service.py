from sqlalchemy.orm import Session
from app.config import settings
from app.models.flight_price import FlightPrice
from app.models.monitor_task import MonitorTask
from app.services.alert_service import create_alert
from app.services.date_service import next_target_dates
from app.services.provider_service import ProviderService

provider_service = ProviderService()


def run_check(db: Session, task: MonitorTask):
    for d in next_target_dates(settings.target_dates_count):
        rows = provider_service.search_all(db, task.id, task.origin_city, task.destination_city, d)
        for row in rows:
            fp = FlightPrice(task_id=task.id, target_date=d, **row)
            db.add(fp)
            db.commit()
            db.refresh(fp)
            if row["adult_price"] <= task.max_price:
                create_alert(db, task.id, fp.id, f"命中低价: {row['flight_no']} ¥{row['adult_price']}")


def run_all_enabled_tasks(db: Session):
    for task in db.query(MonitorTask).filter(MonitorTask.enabled.is_(True)).all():
        run_check(db, task)
