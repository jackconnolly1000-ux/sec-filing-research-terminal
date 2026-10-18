"""Bounded request coordination and deployment-only module refresh; no network calls."""
from collections import OrderedDict
from contextlib import contextmanager
import hashlib
import importlib
from threading import RLock
import time


class ResponseStore:
    def __init__(self, ttl=3600, max_entries=64, clock=time.time):
        self.ttl, self.max_entries, self.clock = ttl, max_entries, clock
        self._values, self._flights, self._lock = OrderedDict(), {}, RLock()

    def _expire(self):
        for key, value in list(self._values.items()):
            if self.clock() - value["at"] >= self.ttl:
                del self._values[key]

    def get(self, key):
        with self._lock:
            self._expire()
            value = self._values.get(key)
            if value is not None:
                self._values.move_to_end(key)
            return value

    def __setitem__(self, key, value):
        with self._lock:
            self._expire()
            self._values[key] = value
            self._values.move_to_end(key)
            while len(self._values) > self.max_entries:
                self._values.popitem(last=False)

    @contextmanager
    def request(self, key):
        with self._lock:
            lock, users = self._flights.get(key, (RLock(), 0))
            self._flights[key] = (lock, users + 1)
        try:
            with lock:
                yield
        finally:
            with self._lock:
                lock, users = self._flights[key]
                if users == 1:
                    del self._flights[key]
                else:
                    self._flights[key] = (lock, users - 1)


_deployment_lock = RLock()


def refresh_modules(modules):
    """Keep caches on reruns; reload dependency order only after code or checked constants change."""
    from pathlib import Path
    with _deployment_lock:
        changed = False
        for module in modules:
            path = Path(module.__file__)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            old = getattr(module, "_loaded_source_hash", None)
            expected = getattr(module, "_loaded_checked_hash", None)
            invalid = (module.__name__ == "theme" and not hasattr(module, "FLOW_IN"))
            invalid |= expected is not None and getattr(module, "CHECKED_SHA256", None) != expected
            if old != digest or invalid or changed:
                importlib.reload(module)
                changed = True
                module._loaded_source_hash = digest
                module._loaded_checked_hash = getattr(module, "CHECKED_SHA256", None)
