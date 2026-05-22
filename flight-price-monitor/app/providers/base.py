from abc import ABC, abstractmethod
from datetime import date


class BaseFlightProvider(ABC):
    name = "base"

    @abstractmethod
    def search(self, origin: str, destination: str, target_date: date) -> list[dict]:
        raise NotImplementedError
