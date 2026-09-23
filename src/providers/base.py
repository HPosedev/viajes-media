from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional
from src.core.models import (
    Accommodation,
    AccommodationType,
    Segment,
    Station,
)


class RailDataProvider(ABC):
    """Abstract interface for rail network data sources (GTFS or Seed Graph)."""

    @abstractmethod
    def get_all_stations(self) -> List[Station]:
        """Returns all registered railway stations."""
        pass

    @abstractmethod
    def get_all_segments(self) -> List[Segment]:
        """Returns all direct railway segments between stations."""
        pass

    def find_station(self, query: str) -> Optional[Station]:
        """
        Finds a station by name, city, code, or alias.
        Matches are ranked: exact ID > exact name/city > exact alias > partial (accent-insensitive).
        """
        if not query or not query.strip():
            return None

        stations = self.get_all_stations()
        q = query.strip().lower()

        # 1. Exact ID match
        upper_q = query.strip().upper()
        for s in stations:
            if s.id.upper() == upper_q:
                return s

        # 2. Exact name or city match
        for s in stations:
            if s.name.lower() == q or s.city.lower() == q:
                return s

        # 3. Exact alias match
        for s in stations:
            if any(alias.lower() == q for alias in s.aliases):
                return s

        # 4. Partial substring match
        for s in stations:
            if s.matches_query(q):
                return s

        return None


class AccommodationProvider(ABC):
    """Abstract interface for lodging providers (Booking, Airbnb, RapidAPI, Mock, Scraper)."""

    @abstractmethod
    def search(
        self,
        destination_name: str,
        acc_type: AccommodationType = AccommodationType.BOTH,
        min_rating: Optional[float] = None,
        max_price: Optional[float] = None,
        checkin_date: Optional[date] = None,
        checkout_date: Optional[date] = None,
    ) -> List[Accommodation]:
        """
        Searches available accommodations for a destination city/town.
        Returns a list of Accommodation models matching criteria.
        """
        pass
