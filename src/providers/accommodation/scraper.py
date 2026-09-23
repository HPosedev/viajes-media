from datetime import date
import logging
from typing import List, Optional

from src.core.models import Accommodation, AccommodationType
from src.providers.base import AccommodationProvider
from src.providers.accommodation.mock_provider import MockAccommodationProvider

logger = logging.getLogger(__name__)


class ScraperAccommodationProvider(AccommodationProvider):
    """
    Placeholder for a controlled web scraping provider of public accommodation directories.

    No scraping source is implemented yet, so every search is delegated to the fallback
    provider (MockAccommodationProvider by default). Implement the HTML fetching/parsing
    in `search` and keep the fallback for blocked or failed requests.
    """

    def __init__(self, fallback_provider: Optional[AccommodationProvider] = None):
        self.fallback = fallback_provider or MockAccommodationProvider()

    def search(
        self,
        destination_name: str,
        acc_type: AccommodationType = AccommodationType.BOTH,
        min_rating: Optional[float] = None,
        max_price: Optional[float] = None,
        checkin_date: Optional[date] = None,
        checkout_date: Optional[date] = None,
    ) -> List[Accommodation]:
        logger.info("Scraper provider not implemented yet. Using fallback accommodation provider.")
        return self.fallback.search(destination_name, acc_type, min_rating, max_price, checkin_date, checkout_date)
