import time
import threading

class SimpleTTLCache:
    def __init__(self):
        self.store = {}
        self.last_valid = {}
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key):
        with self.lock:
            if key in self.store:
                entry = self.store[key]
                if entry["expiry"] > time.time():
                    self.hits += 1
                    return entry["data"]
                else:
                    del self.store[key]

            self.misses += 1
        return None

    def set(self, key, value, ttl):
        with self.lock:
            self.store[key] = {
                "data": value,
                "expiry": time.time() + ttl
            }
            self.last_valid[key] = value  # salva última válida

    def get_last_valid(self, key):
        with self.lock:
            return self.last_valid.get(key)

    def stats(self):
        with self.lock:
            return {
                "keys": len(self.store),
                "hits": self.hits,
                "misses": self.misses
            }

cache = SimpleTTLCache()