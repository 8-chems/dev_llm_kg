from collections import defaultdict


class MetricsRegistry:

    def __init__(self):
        self._counters: dict[str, int] = defaultdict(int)

    def inc(self, metric: str, value: int = 1):
        self._counters[metric] += value

    def get_all() -> dict[str, int]:
        return dict(self._counters)


metrics = MetricsRegistry()
