from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import SessionLocal
from app.services.monitor_service import run_all_enabled_tasks

scheduler = BackgroundScheduler()


def scheduled_job():
    db = SessionLocal()
    try:
        run_all_enabled_tasks(db)
    finally:
        db.close()


def start_scheduler():
    if scheduler.running:
        return
    scheduler.add_job(
        scheduled_job,
        "interval",
        minutes=settings.check_interval_minutes,
        id="monitor_job",
        replace_existing=True,
    )
    scheduler.start()
