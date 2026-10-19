"""Small interchangeable JSON cache implementations."""

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Protocol


class Cache(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any, ttl_seconds: int) -> None: ...
    def clear(self) -> None: ...


class NoCache:
    def get(self, key: str) -> None:
        return None

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        return None

    def clear(self) -> None:
        return None


class MemoryCache:
    def __init__(self):
        self._values: dict[str, tuple[float, Any]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._values.get(key)
            if item is None:
                return None
            expires, value = item
            if expires <= time.time():
                self._values.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        with self._lock:
            self._values[key] = (time.time() + ttl_seconds, value)

    def clear(self) -> None:
        with self._lock:
            self._values.clear()


class SQLiteCache:
    def __init__(self, path: str):
        self.path = str(Path(path).expanduser())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS cache ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL, expires REAL NOT NULL)"
            )

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def get(self, key: str) -> Any | None:
        with self._connect() as connection:
            row = connection.execute("SELECT value, expires FROM cache WHERE key = ?", (key,)).fetchone()
            if row is None:
                return None
            value, expires = row
            if expires <= time.time():
                connection.execute("DELETE FROM cache WHERE key = ?", (key,))
                return None
            return json.loads(value)

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO cache(key, value, expires) VALUES(?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, expires=excluded.expires",
                (key, json.dumps(value, ensure_ascii=False), time.time() + ttl_seconds),
            )

    def clear(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM cache")
