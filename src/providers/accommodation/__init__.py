from typing import Optional
from src.config import settings
from src.providers.base import AccommodationProvider
from src.providers.accommodation.mock_provider import MockAccommodationProvider
from src.providers.accommodation.rapidapi import RapidApiBookingProvider
from src.providers.accommodation.scraper import ScraperAccommodationProvider


def get_accommodation_provider(provider_name: Optional[str] = None) -> AccommodationProvider:
    """Factory creating the appropriate AccommodationProvider based on settings or parameter."""
    chosen = (provider_name or settings.ACCOMMODATION_PROVIDER).strip().lower()

    if chosen == "rapidapi":
        return RapidApiBookingProvider()
    elif chosen == "scraper":
        return ScraperAccommodationProvider()
    else:
        return MockAccommodationProvider()
