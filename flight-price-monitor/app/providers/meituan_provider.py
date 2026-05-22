from datetime import date
from app.providers.base import BaseFlightProvider


class MeituanProvider(BaseFlightProvider):
    name = "meituan"

    def search(self, origin: str, destination: str, target_date: date) -> list[dict]:
        return []
