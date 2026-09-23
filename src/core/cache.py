from contextlib import contextmanager
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterator, Optional
from src.config import settings


class SQLiteCache:
    """Thread-safe SQLite persistent cache with time-to-live (TTL) support."""

    def __init__(self, db_path: Optional[Path] = None, default_ttl_hours: Optional[int] = None):
        self.db_path = db_path or settings.SQLITE_CACHE_DB
        self.default_ttl_seconds = (default_ttl_hours or settings.CACHE_TTL_HOURS) * 3600
        self._ensure_db()

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Opens a connection, commits on success / rolls back on error, and always closes it.

        (sqlite3.Connection's own context manager only handles the transaction,
        it never closes the connection.)
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _ensure_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_store (
                    cache_key TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_store(expires_at)"
            )

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT data_json, expires_at FROM cache_store WHERE cache_key = ?",
                (key,)
            )
            row = cur.fetchone()
            if not row:
                return None
            if row["expires_at"] < now:
                # Expired
                cur.execute("DELETE FROM cache_store WHERE cache_key = ?", (key,))
                return None
            try:
                return json.loads(row["data_json"])
            except json.JSONDecodeError:
                return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        now = time.time()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expires_at = now + ttl
        data_json = json.dumps(value, ensure_ascii=False)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO cache_store (cache_key, data_json, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    data_json=excluded.data_json,
                    created_at=excluded.created_at,
                    expires_at=excluded.expires_at
                """,
                (key, data_json, now, expires_at)
            )

    def delete(self, key: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM cache_store WHERE cache_key = ?", (key,))

    def clear(self) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM cache_store")

    def prune_expired(self) -> int:
        now = time.time()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM cache_store WHERE expires_at < ?", (now,))
            return cur.rowcount
