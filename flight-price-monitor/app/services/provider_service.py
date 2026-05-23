import json
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
                status = "success"
                reason = f"{target_date.isoformat()} returned {len(provider_rows)} flights"
                if not provider_rows:
                    status = "no_results"
                    diagnostics = getattr(provider, "last_diagnostics", None)
                    if diagnostics:
                        details = json.dumps(diagnostics, ensure_ascii=False, separators=(",", ":"))
                        reason = f"{reason}; diagnostics={details}"
                db.add(
                    ProviderLog(
                        provider=provider.name,
                        task_id=task_id,
                        status=status,
                        reason=reason[:1000],
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
