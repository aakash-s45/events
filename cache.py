import time
from typing import Any, Optional


class InMemoryCache:
    def __init__(self):
        self._store = {}

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Store a key-value pair in the cache with an optional time-to-live (ttl) in seconds.
        """
        expire_at = time.time() + ttl if ttl is not None else None
        self._store[key] = {"value": value, "expire_at": expire_at}

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache. Returns None if the key is missing or expired.
        """
        item = self._store.get(key)
        if item is None:
            return None

        if item["expire_at"] is not None and time.time() > item["expire_at"]:
            self._store.pop(key, None)
            return None

        return item["value"]

    def delete(self, key: str):
        """
        Remove a key from the cache.
        """
        self._store.pop(key, None)

    def ttl(self, key: str) -> Optional[int]:
        """
        Return the TTL (time to live) in seconds for a key. 
        Returns None if no TTL is set, or -1 if the key does not exist or has expired.
        """
        item = self._store.get(key)
        if item is None:
            return -1

        expire_at = item["expire_at"]
        if expire_at is None:
            return None

        remaining = expire_at - time.time()
        if remaining <= 0:
            self._store.pop(key, None)
            return -1

        return int(remaining)

    def expire(self, key: str, ttl: int) -> bool:
        """
        Update the TTL for a given key.
        Returns True if successful, False if the key does not exist or has expired.
        """
        item = self._store.get(key)
        if item is None:
            return False

        if item["expire_at"] is not None and time.time() > item["expire_at"]:
            self._store.pop(key, None)
            return False

        item["expire_at"] = time.time() + ttl
        return True
