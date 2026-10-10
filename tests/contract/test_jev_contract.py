import pytest
from src.app.config import Settings
from src.app.clients.breaker import Breaker
from src.app.clients.jev import JevClient


@pytest.mark.asyncio
async def test_jev_client_decide_contract():
    settings = Settings()
    breaker = Breaker()
    client = JevClient(settings, breaker)

    state = {"question": {"untrusted": "Where is Acme Corp?"}}
    questions = {"resolve": None}

    class MockQ:
        criteria = {"c0": "Acme Corp", "none": "None"}

    result, latency_ms = await client.decide(
        state, {"resolve": MockQ()}
    )

    assert latency_ms >= 0
    assert hasattr(result, "choices")
    assert "resolve" in result.choices
    assert result.choices["resolve"].choice in ["c0", "none"]
    assert "c0" in result.choices["resolve"].probabilities
