import time
import asyncio
from collections import deque


class BreakerOpenException(Exception):
    """Raised when the circuit breaker is open."""

    pass


class Breaker:

    def __init__(
        self,
        failure_rate_threshold: float = 0.50,
        window_size: int = 20,
        p95_threshold_s: float = 2.0,
        probe_interval_s: float = 30.0,
    ):
        self.failure_rate_threshold = failure_rate_threshold
        self.window_size = window_size
        self.p95_threshold_s = p95_threshold_s
        self.probe_interval_s = probe_interval_s

        self._results: deque[bool] = deque(maxlen=window_size)
        self._latencies: deque[tuple[float, float]] = deque()  # (timestamp, latency_s)

        self._state: str = "closed"  # "closed", "open", "half_open"
        self._opened_at: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def open(self) -> bool:
        now = time.monotonic()
        if self._state == "open":
            if now - self._opened_at >= self.probe_interval_s:
                self._state = "half_open"
                return False
            return True
        return False

    @property
    def state(self) -> str:
        return self._state

    def record_success(self, latency_s: float = 0.0) -> None:
        now = time.monotonic()
        self._results.append(True)
        self._latencies.append((now, latency_s))
        self._cleanup_latencies(now)

        if self._state == "half_open":
            self._state = "closed"

        self._check_trip(now)

    def record_failure(self) -> None:
        now = time.monotonic()
        self._results.append(False)
        self._cleanup_latencies(now)

        if self._state == "half_open":
            self._trip(now)
        else:
            self._check_trip(now)

    def _cleanup_latencies(self, now: float) -> None:
        # Keep latencies from the last 60 seconds
        cutoff = now - 60.0
        while self._latencies and self._latencies[0][0] < cutoff:
            self._latencies.popleft()

    def _check_trip(self, now: float) -> None:
        if len(self._results) >= 5:
            failures = self._results.count(False)
            rate = failures / len(self._results)
            if rate > self.failure_rate_threshold:
                self._trip(now)
                return

        # Check p95 latency over 1 min
        if len(self._latencies) >= 10:
            lats = sorted([lat for _, lat in self._latencies])
            p95_idx = int(len(lats) * 0.95)
            p95 = lats[p95_idx]
            if p95 > self.p95_threshold_s:
                self._trip(now)

    def _trip(self, now: float) -> None:
        self._state = "open"
        self._opened_at = now
