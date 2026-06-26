import time
import threading
from typing import Optional, Any

class SimpleMemoryCache:
    """A lightweight thread-safe TTL cache for search query caching."""
    def __init__(self, ttl_seconds: int = 300, max_size: int = 500):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self.store = {}
        self.lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.store:
                val, expiry = self.store[key]
                if time.time() < expiry:
                    return val
                else:
                    self.store.pop(key, None)
            return None

    def set(self, key: str, value: Any):
        with self.lock:
            if len(self.store) >= self.max_size and key not in self.store:
                # Evict oldest (FIFO)
                oldest_key = next(iter(self.store), None)
                if oldest_key is not None:
                    self.store.pop(oldest_key, None)
            self.store[key] = (value, time.time() + self.ttl)

    def clear(self):
        with self.lock:
            self.store.clear()

# Shared RAG cache instance
rag_cache = SimpleMemoryCache(ttl_seconds=300)
