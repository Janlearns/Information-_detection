"""Process-local pacing/cache for the existing search provider, not a quota bypass."""
from collections import OrderedDict
from copy import deepcopy
import math
import threading
import time

from app.search_status import error_kind


class SearchPaused(RuntimeError):
    def __init__(self, kind, retry_after):
        super().__init__('Pencarian dijeda sementara.')
        self.kind = kind
        self.retry_after = retry_after


class SearchSession:
    def __init__(self, interval=2., ttl=300., capacity=128, clock=None, sleep=None):
        self.interval, self.ttl, self.capacity = interval, ttl, capacity
        self.clock, self.sleep = clock or time.monotonic, sleep or time.sleep
        self.cache = OrderedDict()
        self.next_request = 0.
        self.paused_until = 0.
        self.pause_kind = 'rate_limit'
        self.rate_strikes = 0
        self.transport_failures = 0
        self.lock = threading.Lock()

    def query(self, engine, query):
        key = ' '.join(query.casefold().split())
        with self.lock:
            now = self.clock()
            for expired in [key for key, (expiry, _) in self.cache.items() if expiry <= now]:
                del self.cache[expired]
            if key in self.cache:
                _, rows = self.cache[key]
                self.cache.move_to_end(key)
                return deepcopy(rows), True
            if now < self.paused_until:
                raise SearchPaused(self.pause_kind, math.ceil(self.paused_until - now))
            delay = max(0., self.next_request - now)
            if delay:
                self.sleep(delay)
            try:
                rows = list(engine.text(query, max_results=12))
            except Exception as exc:
                kind = error_kind(exc)
                if kind == 'rate_limit':
                    self.rate_strikes = min(self.rate_strikes + 1, 4)
                    self.pause_kind = kind
                    self.paused_until = self.clock() + min(300, 60 * 2 ** (self.rate_strikes - 1))
                elif kind in {'timeout', 'connection'}:
                    self.transport_failures += 1
                    if self.transport_failures >= 3:
                        self.pause_kind = kind
                        self.paused_until = self.clock() + 15
                raise
            else:
                self.transport_failures = 0
                self.rate_strikes = 0
                if rows:
                    self.cache[key] = (self.clock() + self.ttl, deepcopy(rows))
                    self.cache.move_to_end(key)
                    while len(self.cache) > self.capacity:
                        self.cache.popitem(last=False)
                return rows, False
            finally:
                self.next_request = self.clock() + self.interval

    def retry_after(self):
        with self.lock:
            return max(0, math.ceil(self.paused_until - self.clock()))
