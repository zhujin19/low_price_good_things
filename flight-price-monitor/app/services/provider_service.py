import time
from datetime import date
from sqlalchemy.orm import Session
from app.models.provider_log import ProviderLog
from app.providers.ctrip_provider import CtripProvider


class ProviderService:
    def __init__(self):
        self.providers = [CtripProvider()]

    def search_all(self, db: Session, task_id: int, origin: str, destination: str, target_date: date) -> list[dict]:
        rows = []
        for provider in self.providers:
            st = time.time()
            try:
                rows.extend(provider.search(origin, destination, target_date))
                db.add(ProviderLog(provider=provider.name, task_id=task_id, status="success", reason=None, duration_ms=int((time.time() - st) * 1000)))
            except Exception as e:
                db.add(ProviderLog(provider=provider.name, task_id=task_id, status="failed", reason=str(e), duration_ms=int((time.time() - st) * 1000)))
            db.commit()
        return rows
