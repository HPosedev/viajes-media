from datetime import date
import logging
from typing import List, Optional
import urllib.parse
import httpx

from src.config import settings
from src.core.models import Accommodation, AccommodationType
from src.providers.base import AccommodationProvider
from src.providers.accommodation.mock_provider import MockAccommodationProvider

logger = logging.getLogger(__name__)


class RapidApiBookingProvider(AccommodationProvider):
    """
    Accommodation provider querying RapidAPI Booking.com / Airbnb aggregator endpoints.
    Falls back gracefully to MockAccommodationProvider if API key is unset,
    network fails, or quota is exceeded.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_host: Optional[str] = None,
        fallback_provider: Optional[AccommodationProvider] = None
    ):
        self.api_key = api_key or settings.RAPIDAPI_KEY
        self.api_host = api_host or settings.RAPIDAPI_HOST
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
        # If API key is empty or placeholder, use fallback immediately
        if not self.api_key or "tu_api_key" in self.api_key:
            logger.info("RapidAPI key not set. Using offline mock accommodation provider.")
            return self.fallback.search(destination_name, acc_type, min_rating, max_price, checkin_date, checkout_date)

        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host
        }

        try:
            # Query destination ID first
            clean_name = destination_name.split("-")[0].strip()
            with httpx.Client(timeout=8.0) as client:
                dest_url = f"https://{self.api_host}/api/v1/hotels/searchDestination"
                resp = client.get(dest_url, headers=headers, params={"query": clean_name})
                if resp.status_code != 200:
                    logger.warning("RapidAPI returned status %s: %s. Using fallback.", resp.status_code, resp.text[:200])
                    return self.fallback.search(destination_name, acc_type, min_rating, max_price, checkin_date, checkout_date)

                data = resp.json()
                dest_id = None
                if data.get("data"):
                    dest_id = data["data"][0].get("dest_id")

                if not dest_id:
                    return self.fallback.search(destination_name, acc_type, min_rating, max_price, checkin_date, checkout_date)

                # Search hotels in destination
                search_url = f"https://{self.api_host}/api/v1/hotels/searchHotels"
                params = {
                    "dest_id": dest_id,
                    "search_type": "CITY",
                    "adults": "2",
                    "page_number": "1"
                }
                if checkin_date:
                    params["arrival_date"] = checkin_date.strftime("%Y-%m-%d")
                if checkout_date:
                    params["departure_date"] = checkout_date.strftime("%Y-%m-%d")

                h_resp = client.get(search_url, headers=headers, params=params)
                if h_resp.status_code != 200:
                    return self.fallback.search(destination_name, acc_type, min_rating, max_price, checkin_date, checkout_date)

                h_data = h_resp.json()
                hotels = h_data.get("data", {}).get("hotels", [])

                nights_count = max(1, (checkout_date - checkin_date).days) if (checkin_date and checkout_date) else 1

                results: List[Accommodation] = []
                for h in hotels:
                    p = h.get("property", {})
                    name = p.get("name", "Alojamiento")
                    score = float(p.get("reviewScore", 8.0) or 8.0)
                    reviews = int(p.get("reviewCount", 100) or 100)

                    # In Booking.com API, grossPrice is the TOTAL price for the entire stay (all nights requested)
                    total_stay_price = float(p.get("priceBreakdown", {}).get("grossPrice", {}).get("value", 85.0 * nights_count) or (85.0 * nights_count))
                    price_per_night = round(total_stay_price / nights_count, 1)

                    # Determine type
                    is_apartment = "apartment" in name.lower() or "apartamento" in name.lower()
                    item_type = AccommodationType.APARTMENT if is_apartment else AccommodationType.HOTEL

                    if acc_type != AccommodationType.BOTH and item_type != acc_type:
                        continue
                    if min_rating is not None and score < min_rating:
                        continue
                    if max_price is not None and price_per_night > max_price:
                        continue

                    hotel_id = str(p.get("id", ""))
                    b_url = p.get("url") or p.get("deep_link")
                    if not b_url:
                        # Avoid generating broken /hotel/es/{numeric_id}.es.html URLs which 404 on Booking
                        quoted_query = urllib.parse.quote_plus(f"{name} {clean_name}")
                        b_url = f"https://www.booking.com/searchresults.es.html?ss={quoted_query}"

                    if checkin_date and checkout_date:
                        cin = checkin_date.isoformat()
                        cout = checkout_date.isoformat()
                        sep = "&" if "?" in b_url else "?"
                        b_url += f"{sep}checkin={cin}&checkout={cout}&group_adults=2&no_rooms=1"

                    results.append(
                        Accommodation(
                            id=f"rapid_{hotel_id}",
                            name=name,
                            destination_city=clean_name,
                            type=item_type,
                            price_per_night=price_per_night,
                            currency="EUR",
                            rating=score,
                            reviews_count=reviews,
                            address=p.get("wishlistName") or f"Centro de {clean_name}",
                            booking_url=b_url,
                            image_url=p.get("photoUrls", [None])[0] if p.get("photoUrls") else None,
                            checkin_date=checkin_date,
                            checkout_date=checkout_date,
                            nights_count=nights_count,
                            total_price=round(total_stay_price, 0)
                        )
                    )

                # The API answered with real listings: return them even if the filters left
                # nothing, instead of mixing in simulated offline data.
                if hotels:
                    return results

        except Exception as e:
            logger.error("RapidAPI query failed: %s. Using fallback.", e)

        return self.fallback.search(destination_name, acc_type, min_rating, max_price, checkin_date, checkout_date)
