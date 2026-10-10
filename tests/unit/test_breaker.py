from src.app.clients.breaker import Breaker


def test_breaker_initial_closed():
    b = Breaker(failure_rate_threshold=0.5, window_size=5)
    assert not b.open
    assert b.state == "closed"


def test_breaker_trips_on_failures():
    b = Breaker(failure_rate_threshold=0.5, window_size=5)
    for _ in range(5):
        b.record_failure()
    assert b.open
    assert b.state == "open"


def test_breaker_recovers_after_success():
    b = Breaker(failure_rate_threshold=0.5, window_size=5)
    b.record_success(0.1)
    b.record_success(0.1)
    assert not b.open
