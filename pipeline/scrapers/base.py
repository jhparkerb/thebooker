from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date
from pipeline.optimizer import Showing


class Scraper(ABC):
    @abstractmethod
    def fetch(self, theater_id: str, day: date) -> list[Showing]:
        """Return all showings for one theater on one day."""
        ...
