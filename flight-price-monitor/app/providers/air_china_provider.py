from datetime import date
from app.providers.base import BaseFlightProvider


class AirChinaProvider(BaseFlightProvider):
    name = "air_china"

    def search(self, origin: str, destination: str, target_date: date) -> list[dict]:
        return []
