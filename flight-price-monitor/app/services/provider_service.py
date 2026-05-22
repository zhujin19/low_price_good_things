import time
from datetime import date

from sqlalchemy.orm import Session

from app.models.provider_log import ProviderLog
from app.providers.ctrip_provider import CtripProvider


class ProviderService:
    def __init__(self):
        self.providers = [CtripProvider()]

    def search_all(
        self,
        db: Session,
        task_id: int,
        origin: str,
        destination: str,
        target_date: date,
    ) -> list[dict]:
        rows = []
        for provider in self.providers:
            started_at = time.time()
            try:
                provider_rows = provider.search(origin, destination, target_date)
                rows.extend(provider_rows)
                reason = f"{target_date.isoformat()} returned {len(provider_rows)} flights"
                db.add(
                    ProviderLog(
                        provider=provider.name,
                        task_id=task_id,
                        status="success",
                        reason=reason,
                        duration_ms=int((time.time() - started_at) * 1000),
                    )
                )
            except Exception as exc:
                db.add(
                    ProviderLog(
                        provider=provider.name,
                        task_id=task_id,
                        status="failed",
                        reason=str(exc)[:1000],
                        duration_ms=int((time.time() - started_at) * 1000),
                    )
                )
            db.commit()
        return rows
