import pytest
from src.core.models import Accommodation, AccommodationType
from src.core.router import RailRouter
from src.providers.rail.local_graph import LocalGraphRailProvider
from src.providers.accommodation.mock_provider import MockAccommodationProvider
from src.core.cache import SQLiteCache


@pytest.fixture
def temp_cache(tmp_path):
    db_file = tmp_path / "test_cache.db"
    return SQLiteCache(db_path=db_file, default_ttl_hours=1)


@pytest.fixture
def rail_provider():
    return LocalGraphRailProvider()


@pytest.fixture
def router(rail_provider, temp_cache):
    return RailRouter(rail_provider=rail_provider, cache=temp_cache)


@pytest.fixture
def acc_provider():
    return MockAccommodationProvider()


@pytest.fixture
def sample_accommodations():
    return [
        Accommodation(
            id="acc_1",
            name="Hotel Lujo Central",
            destination_city="Santiago de Compostela",
            type=AccommodationType.HOTEL,
            price_per_night=200.0,
            rating=9.5,
            reviews_count=1500,
            address="Plaza Mayor 1",
            booking_url="https://booking.com/1",
        ),
        Accommodation(
            id="acc_2",
            name="Apartamento Económico Centro",
            destination_city="Santiago de Compostela",
            type=AccommodationType.APARTMENT,
            price_per_night=60.0,
            rating=8.8,
            reviews_count=350,
            address="Rúa do Vilar 10",
            booking_url="https://airbnb.es/2",
        ),
        Accommodation(
            id="acc_3",
            name="Hostal Básico",
            destination_city="Santiago de Compostela",
            type=AccommodationType.HOTEL,
            price_per_night=45.0,
            rating=7.2,
            reviews_count=120,
            address="Rúa de San Pedro 5",
            booking_url="https://booking.com/3",
        ),
        Accommodation(
            id="acc_4",
            name="Ático Gran Confort",
            destination_city="Santiago de Compostela",
            type=AccommodationType.APARTMENT,
            price_per_night=120.0,
            rating=9.2,
            reviews_count=800,
            address="Rúa Nova 25",
            booking_url="https://airbnb.es/4",
        )
    ]
