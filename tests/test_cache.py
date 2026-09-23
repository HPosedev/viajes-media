import time
from src.core.cache import SQLiteCache


def test_sqlite_cache_set_and_get(temp_cache: SQLiteCache):
    temp_cache.set("key1", {"city": "Santiago", "duration": 28})
    val = temp_cache.get("key1")
    assert val is not None
    assert val["city"] == "Santiago"
    assert val["duration"] == 28


def test_sqlite_cache_miss(temp_cache: SQLiteCache):
    assert temp_cache.get("non_existent_key") is None


def test_sqlite_cache_expiration(tmp_path):
    # Cache with 1 second TTL
    db_file = tmp_path / "exp_cache.db"
    cache = SQLiteCache(db_path=db_file, default_ttl_hours=1)
    cache.set("short_lived", {"data": "hello"}, ttl_seconds=1)

    assert cache.get("short_lived") is not None
    time.sleep(1.1)
    assert cache.get("short_lived") is None


def test_sqlite_cache_delete(temp_cache: SQLiteCache):
    temp_cache.set("delete_me", "value")
    assert temp_cache.get("delete_me") == "value"
    temp_cache.delete("delete_me")
    assert temp_cache.get("delete_me") is None


def test_sqlite_cache_stores_empty_list(temp_cache: SQLiteCache):
    temp_cache.set("no_routes", [])
    assert temp_cache.get("no_routes") == []
