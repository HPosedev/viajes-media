from datetime import date
from typing import Optional
import urllib.parse


def booking_search_url(
    query: str,
    checkin: Optional[date] = None,
    checkout: Optional[date] = None,
    apartments_only: bool = False,
) -> str:
    """
    Booking.com search link. With a property name in `query` ("Hotel Rosi, Benicarló") Booking
    lists that property first; unlike guessed /hotel/es/<slug> pages it can never 404.
    """
    params = {"ss": query}
    if apartments_only:
        params["nflt"] = "ht_id=201"
    if checkin and checkout:
        params.update(checkin=checkin.isoformat(), checkout=checkout.isoformat(), group_adults="2", no_rooms="1")
    return f"https://www.booking.com/searchresults.es.html?{urllib.parse.urlencode(params)}"


def airbnb_search_url(city: str, checkin: Optional[date] = None, checkout: Optional[date] = None) -> str:
    """Airbnb search of homes in a city (Airbnb has no search by listing name)."""
    url = f"https://www.airbnb.es/s/{urllib.parse.quote(city.replace(' ', '-'))}/homes"
    if checkin and checkout:
        url += f"?{urllib.parse.urlencode({'checkin': checkin.isoformat(), 'checkout': checkout.isoformat()})}"
    return url
