from datetime import date
from app.providers.base import BaseFlightProvider


class ChinaSouthernProvider(BaseFlightProvider):
    name = "china_southern"

    def search(self, origin: str, destination: str, target_date: date) -> list[dict]:
        return []
