from src.core.models import (
    Accommodation,
    AccommodationType,
    FilterParams,
    SortCriterion,
)
from src.core.sorter import filter_and_sort_accommodations, calculate_value_score
from src.providers.accommodation.mock_provider import MockAccommodationProvider


def test_accommodation_type_filtering(sample_accommodations):
    # Filter hotels only
    filter_hotel = FilterParams(accommodation_type=AccommodationType.HOTEL)
    hotels = filter_and_sort_accommodations(sample_accommodations, filter_hotel)
    assert len(hotels) == 2
    assert all(h.type == AccommodationType.HOTEL for h in hotels)

    # Filter apartments only
    filter_apt = FilterParams(accommodation_type=AccommodationType.APARTMENT)
    apts = filter_and_sort_accommodations(sample_accommodations, filter_apt)
    assert len(apts) == 2
    assert all(a.type == AccommodationType.APARTMENT for a in apts)

    # Filter both
    filter_both = FilterParams(accommodation_type=AccommodationType.BOTH)
    both = filter_and_sort_accommodations(sample_accommodations, filter_both)
    assert len(both) == 4


def test_accommodation_sorting_by_rating(sample_accommodations):
    filter_rating = FilterParams(
        accommodation_type=AccommodationType.BOTH,
        sort_by=SortCriterion.BEST_RATING
    )
    sorted_items = filter_and_sort_accommodations(sample_accommodations, filter_rating)
    ratings = [x.rating for x in sorted_items]
    assert ratings == sorted(ratings, reverse=True)
    assert sorted_items[0].id == "acc_1"  # 9.5 rating


def test_accommodation_sorting_by_price(sample_accommodations):
    # Lowest price first
    filter_price_asc = FilterParams(
        accommodation_type=AccommodationType.BOTH,
        sort_by=SortCriterion.PRICE_LOWEST
    )
    sorted_asc = filter_and_sort_accommodations(sample_accommodations, filter_price_asc)
    prices_asc = [x.price_per_night for x in sorted_asc]
    assert prices_asc == sorted(prices_asc)
    assert sorted_asc[0].id == "acc_3"  # 45.0 €

    # Highest price first
    filter_price_desc = FilterParams(
        accommodation_type=AccommodationType.BOTH,
        sort_by=SortCriterion.PRICE_HIGHEST
    )
    sorted_desc = filter_and_sort_accommodations(sample_accommodations, filter_price_desc)
    prices_desc = [x.price_per_night for x in sorted_desc]
    assert prices_desc == sorted(prices_desc, reverse=True)
    assert sorted_desc[0].id == "acc_1"  # 200.0 €


def test_accommodation_budget_and_rating_thresholds(sample_accommodations):
    filters = FilterParams(
        accommodation_type=AccommodationType.BOTH,
        min_price=50.0,
        max_price=150.0,
        min_rating=8.5
    )
    filtered = filter_and_sort_accommodations(sample_accommodations, filters)
    assert len(filtered) == 2
    for item in filtered:
        assert 50.0 <= item.price_per_night <= 150.0
        assert item.rating >= 8.5


def test_value_score_calculation():
    # Good rating + low price + good reviews should yield high score
    high_value = Accommodation(
        id="test_good",
        name="Excelente Calidad Precio",
        destination_city="Toledo",
        type=AccommodationType.HOTEL,
        price_per_night=60.0,
        rating=9.2,
        reviews_count=600,
        address="Calle Centro",
        booking_url="https://booking.com",
    )
    # Poor rating + expensive price should yield lower score
    low_value = Accommodation(
        id="test_bad",
        name="Caro y Regular",
        destination_city="Toledo",
        type=AccommodationType.HOTEL,
        price_per_night=180.0,
        rating=7.5,
        reviews_count=40,
        address="Calle Afueras",
        booking_url="https://booking.com",
    )

    score_high = calculate_value_score(high_value, min_price_sample=50.0, max_price_sample=200.0)
    score_low = calculate_value_score(low_value, min_price_sample=50.0, max_price_sample=200.0)

    assert score_high > score_low
    assert 0.0 <= score_high <= 10.0
    assert 0.0 <= score_low <= 10.0


def test_mock_accommodation_provider(acc_provider: MockAccommodationProvider):
    # Test curated town
    results = acc_provider.search("Santiago de Compostela", acc_type=AccommodationType.BOTH)
    assert len(results) > 0
    assert any("Parador" in r.name for r in results)

    # Test unknown town (procedural generation fallback)
    results_unknown = acc_provider.search("Pueblo Desconocido", acc_type=AccommodationType.BOTH)
    assert len(results_unknown) > 0
    assert any(r.type == AccommodationType.HOTEL for r in results_unknown)
    assert any(r.type == AccommodationType.APARTMENT for r in results_unknown)


def test_accommodation_exact_dates_pricing(acc_provider: MockAccommodationProvider):
    from datetime import date
    # Weekend in September (peak season + Friday/Saturday nights)
    cin_weekend = date(2026, 9, 25)  # Friday
    cout_weekend = date(2026, 9, 27)  # Sunday (2 nights)
    weekend_results = acc_provider.search("Benicarló", checkin_date=cin_weekend, checkout_date=cout_weekend)
    assert len(weekend_results) > 0

    first_weekend = weekend_results[0]
    assert first_weekend.nights_count == 2
    assert first_weekend.checkin_date == cin_weekend
    assert first_weekend.checkout_date == cout_weekend
    assert first_weekend.total_price is not None
    assert "checkin=2026-09-25" in first_weekend.booking_url
    assert "checkout=2026-09-27" in first_weekend.booking_url

    # Weekday in November (low season + Monday-Wednesday)
    cin_weekday = date(2026, 11, 9)   # Monday
    cout_weekday = date(2026, 11, 11)  # Wednesday (2 nights)
    weekday_results = acc_provider.search("Benicarló", checkin_date=cin_weekday, checkout_date=cout_weekday)
    first_weekday = weekday_results[0]

    # Weekend rate should be higher than off-season weekday rate for the same accommodation
    assert first_weekend.price_per_night > first_weekday.price_per_night
    assert first_weekend.total_price > first_weekday.total_price

    # Verify realistic total price for 2 nights (calibrated Benicarló pricing)
    assert 50.0 <= first_weekend.total_price <= 220.0
    assert abs(first_weekend.total_price - (first_weekend.price_per_night * first_weekend.nights_count)) <= 2.0


def test_rapidapi_nights_calculation():
    """Verify that grossPrice from Booking.com API (which covers all nights) is divided by nights_count."""
    from unittest.mock import patch, MagicMock
    from src.providers.accommodation.rapidapi import RapidApiBookingProvider

    provider = RapidApiBookingProvider(api_key="valid_test_api_key_123")

    mock_client = MagicMock()
    # Response 1: searchDestination
    resp_dest = MagicMock()
    resp_dest.status_code = 200
    resp_dest.json.return_value = {"status": True, "data": [{"dest_id": "-373059"}]}

    # Response 2: searchHotels
    resp_hotels = MagicMock()
    resp_hotels.status_code = 200
    resp_hotels.json.return_value = {
        "status": True,
        "data": {
            "hotels": [
                {
                    "property": {
                        "id": 12345,
                        "name": "Hotel Booking Test",
                        "reviewScore": 8.5,
                        "reviewCount": 120,
                        # Booking API returns grossPrice = 90.0 for the ENTIRE 2 nights
                        "priceBreakdown": {
                            "grossPrice": {
                                "value": 90.0,
                                "currency": "EUR"
                            }
                        },
                        "wishlistName": "Centro"
                    }
                }
            ]
        }
    }

    mock_client.get.side_effect = [resp_dest, resp_hotels]

    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value = mock_client
        from datetime import date
        checkin = date(2026, 9, 25)
        checkout = date(2026, 9, 27)  # 2 nights
        results = provider.search("Benicarló", checkin_date=checkin, checkout_date=checkout)

    assert len(results) == 1
    acc = results[0]
    assert acc.nights_count == 2
    # 90€ total for 2 nights -> 45€ per night, 90€ total stay (NOT 90€/night and 180€ total)
    assert acc.price_per_night == 45.0
    assert acc.total_price == 90.0
    assert acc.is_live
    assert "checkin=2026-09-25" in acc.booking_url and "/hotel/" not in acc.booking_url


def test_rapidapi_fallback_keeps_stay_dates():
    """If the destination lookup fails, the offline fallback must still price the requested dates."""
    from datetime import date
    from unittest.mock import patch, MagicMock
    from src.providers.accommodation.rapidapi import RapidApiBookingProvider

    provider = RapidApiBookingProvider(api_key="valid_test_api_key_123")
    resp_error = MagicMock(status_code=429, text="Too many requests")
    mock_client = MagicMock()
    mock_client.get.return_value = resp_error

    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value = mock_client
        results = provider.search("Benicarló", checkin_date=date(2026, 9, 25), checkout_date=date(2026, 9, 27))

    assert results
    assert all(r.nights_count == 2 and r.checkin_date == date(2026, 9, 25) for r in results)


def test_rapidapi_does_not_mix_in_mock_data_when_filters_exclude_real_results():
    from unittest.mock import patch, MagicMock
    from src.providers.accommodation.rapidapi import RapidApiBookingProvider

    provider = RapidApiBookingProvider(api_key="valid_test_api_key_123")
    resp_dest = MagicMock(status_code=200)
    resp_dest.json.return_value = {"data": [{"dest_id": "-1"}]}
    resp_hotels = MagicMock(status_code=200)
    resp_hotels.json.return_value = {"data": {"hotels": [
        {"property": {"id": 1, "name": "Hotel Real", "reviewScore": 7.0, "reviewCount": 50,
                      "priceBreakdown": {"grossPrice": {"value": 80.0}}}}
    ]}}
    mock_client = MagicMock()
    mock_client.get.side_effect = [resp_dest, resp_hotels]

    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value = mock_client
        results = provider.search("Benicarló", min_rating=9.0)

    assert results == []


def test_mock_links_never_point_to_guessed_hotel_pages(acc_provider: MockAccommodationProvider):
    """Guessed /hotel/es/<slug> pages 404 on Booking when the slug is wrong."""
    from datetime import date
    from urllib.parse import parse_qs, urlparse

    cin, cout = date(2026, 10, 23), date(2026, 10, 26)
    for city in ["Benicarló", "Castellón de la Plana", "Sagunto", "Xàtiva", "Gandía", "Benicàssim", "Teruel", "Vinaròs"]:
        for acc in acc_provider.search(city, checkin_date=cin, checkout_date=cout):
            assert "/hotel/" not in acc.booking_url, acc.booking_url
            query = parse_qs(urlparse(acc.booking_url).query)
            assert query["checkin"] == ["2026-10-23"]
            assert query["checkout"] == ["2026-10-26"]
            if not acc.is_example:
                # Real properties are searched by their exact name in the destination
                assert "booking.com/searchresults" in acc.booking_url
                assert query["ss"] == [f"{acc.name}, {city}"]


def test_mock_marks_illustrative_listings_as_examples(acc_provider: MockAccommodationProvider):
    # Curated real hotels are not examples
    benicarlo = acc_provider.search("Benicarló")
    names = {r.name: r for r in benicarlo}
    assert "Hotel Rosi" in names and not names["Hotel Rosi"].is_example
    assert "Apartamentos Leman" in names and not names["Apartamentos Leman"].is_example

    # Curated generic apartments link to a city search on Airbnb
    sagunto_examples = [r for r in acc_provider.search("Sagunto") if r.is_example]
    assert sagunto_examples and all("airbnb.es/s/Sagunto/homes" in r.booking_url for r in sagunto_examples)

    # Towns without curated data only get synthetic, clearly marked examples
    synthetic = acc_provider.search("Teruel")
    assert synthetic and all(r.is_example for r in synthetic)
    assert all(not r.is_live for r in benicarlo + synthetic)
