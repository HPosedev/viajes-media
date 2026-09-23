from datetime import date, timedelta
from src.cli.main import next_weekend_dates, parse_stay_dates


def test_parse_stay_dates_valid():
    cin = date.today() + timedelta(days=7)
    cout = cin + timedelta(days=2)
    assert parse_stay_dates(cin.isoformat(), cout.isoformat()) == (cin, cout)


def test_parse_stay_dates_rejects_inconsistent_input():
    cin = date.today() + timedelta(days=7)
    assert parse_stay_dates(cin.isoformat(), cin.isoformat()) == (None, None)  # 0 nights
    assert parse_stay_dates(cin.isoformat(), (cin - timedelta(days=1)).isoformat()) == (None, None)
    assert parse_stay_dates("2020-01-01", "2020-01-03") == (None, None)  # past
    assert parse_stay_dates("25/09/2026", "27/09/2026") == (None, None)  # wrong format
    assert parse_stay_dates(cin.isoformat(), None) == (None, None)  # incomplete
    assert parse_stay_dates(None, None) == (None, None)


def test_next_weekend_dates():
    friday, sunday = next_weekend_dates()
    assert friday.weekday() == 4
    assert 0 <= (friday - date.today()).days < 7
    assert (sunday - friday).days == 2
