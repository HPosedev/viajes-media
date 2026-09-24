from datetime import date
from enum import Enum
from typing import List, Optional
import unicodedata
from pydantic import BaseModel, Field


def _normalize_str(text: str) -> str:
    """Removes diacritics and converts to lowercase for accent-insensitive search."""
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


class AccommodationType(str, Enum):
    HOTEL = "Hoteles"
    APARTMENT = "Apartamentos"
    BOTH = "Ambos"

    @classmethod
    def from_str(cls, value: str) -> "AccommodationType":
        val = value.strip().lower()
        if "hotel" in val:
            return cls.HOTEL
        if "apartamento" in val or "piso" in val:
            return cls.APARTMENT
        return cls.BOTH


class SortCriterion(str, Enum):
    BEST_RATING = "Mejor nota"
    PRICE_LOWEST = "Precio más bajo"
    PRICE_HIGHEST = "Precio más alto"
    VALUE_FOR_MONEY = "Relación calidad/precio"

    @classmethod
    def from_str(cls, value: str) -> "SortCriterion":
        val = value.strip().lower()
        if "nota" in val or "calificaci" in val or "rating" in val:
            return cls.BEST_RATING
        if "bajo" in val or "barato" in val or "asc" in val:
            return cls.PRICE_LOWEST
        if "alto" in val or "caro" in val or "desc" in val:
            return cls.PRICE_HIGHEST
        return cls.VALUE_FOR_MONEY


class Station(BaseModel):
    id: str
    name: str
    city: str
    province: str
    autonomous_community: str
    lat: float
    lon: float
    aliases: List[str] = Field(default_factory=list)

    def matches_query(self, query: str) -> bool:
        q = query.strip().lower()
        if not q:
            return False
        if q in self.name.lower() or q in self.city.lower():
            return True
        if any(q in alias.lower() for alias in self.aliases):
            return True
        q_norm = _normalize_str(q)
        if q_norm in _normalize_str(self.name) or q_norm in _normalize_str(self.city):
            return True
        return any(q_norm in _normalize_str(alias) for alias in self.aliases)


class Segment(BaseModel):
    from_station_id: str
    to_station_id: str
    duration_minutes: int
    train_type: str = "Media Distancia"
    frequency_daily: int = 6
    line: Optional[str] = None


class RouteOption(BaseModel):
    origin: Station
    destination: Station
    total_duration_minutes: int
    is_direct: bool
    segments: List[Segment]
    transfer_station: Optional[Station] = None
    transfer_wait_minutes: int = 0
    estimated_frequency_daily: int = 6

    @property
    def duration_formatted(self) -> str:
        hours = self.total_duration_minutes // 60
        mins = self.total_duration_minutes % 60
        if hours > 0 and mins > 0:
            return f"{hours}h {mins:02d}m"
        elif hours > 0:
            return f"{hours}h"
        return f"{mins}m"

    @property
    def train_types_formatted(self) -> str:
        types = list(dict.fromkeys(s.train_type for s in self.segments))
        return " / ".join(types)


class Accommodation(BaseModel):
    id: str
    name: str
    destination_city: str
    type: AccommodationType
    price_per_night: float
    currency: str = "EUR"
    rating: float  # Scale 0.0 to 10.0
    reviews_count: int
    address: str
    booking_url: str
    image_url: Optional[str] = None
    value_score: float = 0.0  # Quality / price composite score
    checkin_date: Optional[date] = None
    checkout_date: Optional[date] = None
    nights_count: int = 1
    total_price: Optional[float] = None
    is_example: bool = False  # Illustrative listing, not a specific bookable property
    is_live: bool = False  # Price and availability come from a real-time provider

    @property
    def rating_formatted(self) -> str:
        return f"{self.rating:.1f}/10"

    @property
    def price_formatted(self) -> str:
        return f"{self.price_per_night:.0f} €"

    @property
    def total_price_formatted(self) -> str:
        total = self.total_price if self.total_price is not None else (self.price_per_night * self.nights_count)
        if self.nights_count > 1:
            return f"{total:.0f} € ({self.nights_count} noches)"
        return f"{total:.0f} € (1 noche)"


class FilterParams(BaseModel):
    accommodation_type: AccommodationType = AccommodationType.BOTH
    sort_by: SortCriterion = SortCriterion.VALUE_FOR_MONEY
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None
    checkin_date: Optional[date] = None
    checkout_date: Optional[date] = None


class DestinationGetaway(BaseModel):
    destination: Station
    route: RouteOption
    accommodations: List[Accommodation] = Field(default_factory=list)
