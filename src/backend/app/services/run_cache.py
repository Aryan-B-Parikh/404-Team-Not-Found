"""One TTL cache idiom for engine-run memoisation (replaces scattered module globals).

Every cached engine run uses this class: thread-safe double-checked get/set,
per-instance lock, one TTL. Previously the forecast cache checked its TTL outside
its lock and the optimiser cache inside — two idioms for one concern, one of them racy.
"""

from __future__ import annotations

import threading
import time


class TTLCache:
    """Minimal key→value cache with a shared expiry window and a per-instance lock."""

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._key: str | None = None
        self._value: object | None = None
        self._at: float = 0.0

    def get(self, key: str) -> object | None:
        """Return the cached value for ``key`` if present and unexpired, else None."""
        with self._lock:
            if self._key == key and self._value is not None and time.time() - self._at < self._ttl:
                return self._value
            return None

    def set(self, key: str, value: object) -> None:
        with self._lock:
            self._key, self._value, self._at = key, value, time.time()

    def clear(self) -> None:
        with self._lock:
            self._key, self._value, self._at = None, None, 0.0
