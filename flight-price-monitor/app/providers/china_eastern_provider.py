from datetime import date

from app.providers.base import BaseFlightProvider


class ChinaEasternProvider(BaseFlightProvider):
    name = "china_eastern"

    def search(self, origin: str, destination: str, target_date: date) -> list[dict]:
        return []
