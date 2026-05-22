from datetime import date

from app.providers.base import BaseFlightProvider


class FliggyProvider(BaseFlightProvider):
    name = "fliggy"

    def search(self, origin: str, destination: str, target_date: date) -> list[dict]:
        return []
