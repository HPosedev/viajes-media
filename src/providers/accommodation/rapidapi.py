from datetime import date, timedelta
import logging
from typing import Any, Dict, List, Optional, Tuple
import httpx

from src.config import settings
from src.core.cache import SQLiteCache
from src.core.models import Accommodation, AccommodationType
from src.providers.base import AccommodationProvider
from src.providers.accommodation.links import booking_search_url
from src.providers.accommodation.mock_provider import MockAccommodationProvider

logger = logging.getLogger(__name__)

CURRENCY = "EUR"
# Destinations barely change: cache their Booking IDs for a month
DESTINATION_CACHE_SECONDS = 30 * 24 * 3600
# Name keywords used to tell apartments from hotels (the search response has no property type)
APARTMENT_KEYWORDS = ("apartment", "apartamento", "apartament", "apartahotel", "loft", "ático", "atico", "piso", "estudio", "studio", "flat")


class RapidApiBookingProvider(AccommodationProvider):
    """
    Accommodation provider backed by the RapidAPI "Booking COM" API (booking-com15).

    Flow: searchDestination (city -> dest_id) -> searchHotels (live prices for the stay).
    Responses are cached in SQLite so Streamlit reruns and filter changes don't burn the
    API quota. Falls back to MockAccommodationProvider if the API key is unset, the network
    fails, or the quota is exceeded (those results are flagged is_live=False).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_host: Optional[str] = None,
        fallback_provider: Optional[AccommodationProvider] = None,
        cache: Optional[SQLiteCache] = None,
    ):
        self.api_key = api_key or settings.RAPIDAPI_KEY
        self.api_host = api_host or settings.RAPIDAPI_HOST
        self.fallback = fallback_provider or MockAccommodationProvider()
        self.cache = cache or SQLiteCache()

    def search(
        self,
        destination_name: str,
        acc_type: AccommodationType = AccommodationType.BOTH,
        min_rating: Optional[float] = None,
        max_price: Optional[float] = None,
        checkin_date: Optional[date] = None,
        checkout_date: Optional[date] = None,
    ) -> List[Accommodation]:
        # If API key is empty or placeholder, use fallback immediately
        if not self.api_key or "tu_api_key" in self.api_key:
            logger.info("RapidAPI key not set. Using offline mock accommodation provider.")
            return self.fallback.search(destination_name, acc_type, min_rating, max_price, checkin_date, checkout_date)

        # Live prices only exist for concrete dates: default to next Friday -> Saturday
        if not (checkin_date and checkout_date and checkout_date > checkin_date):
            today = date.today()
            checkin_date = today + timedelta(days=(4 - today.weekday()) % 7)
            checkout_date = checkin_date + timedelta(days=1)

        clean_name = destination_name.split("-")[0].strip()
        try:
            with httpx.Client(timeout=10.0, headers={"x-rapidapi-key": self.api_key, "x-rapidapi-host": self.api_host}) as client:
                destination = self._get_destination(client, clean_name)
                hotels = self._get_hotels(client, destination, checkin_date, checkout_date) if destination else None
        except (httpx.HTTPError, ValueError) as e:
            logger.error("RapidAPI query failed: %s. Using fallback.", e)
            hotels = None

        if hotels is None:
            return self.fallback.search(destination_name, acc_type, min_rating, max_price, checkin_date, checkout_date)

        # The API answered with real listings: return them even if the filters leave
        # nothing, instead of mixing in simulated offline data.
        nights_count = (checkout_date - checkin_date).days
        results: List[Accommodation] = []
        for h in hotels:
            acc = self._to_accommodation(h.get("property") or {}, clean_name, checkin_date, checkout_date, nights_count)
            if acc is None:
                continue
            if acc_type != AccommodationType.BOTH and acc.type != acc_type:
                continue
            if min_rating is not None and acc.rating < min_rating:
                continue
            if max_price is not None and acc.price_per_night > max_price:
                continue
            results.append(acc)
        return results

    def _get(self, client: httpx.Client, endpoint: str, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
        resp = client.get(f"https://{self.api_host}/api/v1/hotels/{endpoint}", params=params)
        if resp.status_code != 200:
            logger.warning("RapidAPI %s returned status %s: %s", endpoint, resp.status_code, resp.text[:200])
            return None
        payload = resp.json()
        if payload.get("status") is False:
            logger.warning("RapidAPI %s error: %s", endpoint, str(payload.get("message"))[:200])
            return None
        return payload

    def _get_destination(self, client: httpx.Client, city: str) -> Optional[Tuple[str, str]]:
        """Resolves a city name to Booking's (dest_id, search_type), preferring city results."""
        cache_key = f"rapidapi:dest:{city.lower()}"
        cached = self.cache.get(cache_key)
        if cached:
            return tuple(cached)

        payload = self._get(client, "searchDestination", {"query": city})
        candidates = (payload or {}).get("data") or []
        if not candidates:
            return None
        best = next((d for d in candidates if str(d.get("dest_type", "")).lower() == "city"), candidates[0])
        if not best.get("dest_id"):
            return None
        destination = (str(best["dest_id"]), str(best.get("search_type") or best.get("dest_type") or "city").upper())
        self.cache.set(cache_key, list(destination), ttl_seconds=DESTINATION_CACHE_SECONDS)
        return destination

    def _get_hotels(
        self, client: httpx.Client, destination: Tuple[str, str], checkin: date, checkout: date
    ) -> Optional[List[Dict[str, Any]]]:
        """Returns the raw hotel list for the stay (unfiltered, so filter changes reuse the cache)."""
        dest_id, search_type = destination
        cache_key = f"rapidapi:hotels:{dest_id}:{checkin.isoformat()}:{checkout.isoformat()}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        payload = self._get(client, "searchHotels", {
            "dest_id": dest_id,
            "search_type": search_type,
            "arrival_date": checkin.isoformat(),
            "departure_date": checkout.isoformat(),
            "adults": "2",
            "room_qty": "1",
            "page_number": "1",
            "currency_code": CURRENCY,
            "languagecode": "es",
        })
        if payload is None:
            return None
        hotels = (payload.get("data") or {}).get("hotels") or []
        self.cache.set(cache_key, hotels, ttl_seconds=settings.RAPIDAPI_PRICE_CACHE_HOURS * 3600)
        return hotels

    @staticmethod
    def _to_accommodation(
        p: Dict[str, Any], city: str, checkin: date, checkout: date, nights_count: int
    ) -> Optional[Accommodation]:
        # grossPrice is the TOTAL price for the whole stay (all nights requested)
        gross = (p.get("priceBreakdown") or {}).get("grossPrice") or {}
        if not gross.get("value"):
            return None  # No price: not bookable for these dates
        if gross.get("currency") and gross["currency"] != CURRENCY:
            logger.warning("RapidAPI returned %s prices instead of %s; skipping %s", gross["currency"], CURRENCY, p.get("name"))
            return None
        total_stay_price = float(gross["value"])

        name = p.get("name") or "Alojamiento"
        is_apartment = any(k in name.lower() for k in APARTMENT_KEYWORDS)
        photos = p.get("photoUrls") or []
        return Accommodation(
            id=f"rapid_{p.get('id', '')}",
            name=name,
            destination_city=city,
            type=AccommodationType.APARTMENT if is_apartment else AccommodationType.HOTEL,
            price_per_night=round(total_stay_price / nights_count, 1),
            currency=CURRENCY,
            rating=float(p.get("reviewScore") or 0.0),
            reviews_count=int(p.get("reviewCount") or 0),
            address=p.get("wishlistName") or f"Centro de {city}",
            # The search response carries no property URL; guessed /hotel/ slugs 404
            booking_url=booking_search_url(f"{name}, {city}", checkin, checkout),
            image_url=photos[0] if photos else None,
            checkin_date=checkin,
            checkout_date=checkout,
            nights_count=nights_count,
            total_price=round(total_stay_price, 0),
            is_live=True,
        )
