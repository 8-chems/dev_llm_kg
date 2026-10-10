import asyncio
import pytest
from src.app.clients.jev import JevClient, MockChoiceResult, MockNoulResult, MockSystemOneResult
from src.app.config import Settings
from src.app.clients.breaker import Breaker


@pytest.fixture
def mock_jev_client():
    settings = Settings()
    breaker = Breaker()
    return JevClient(settings, breaker)


def test_generate_mock_choice():
    client = mock_jev_client()
    state = {"test": "state"}
    questions = {"c0": {"criteria": {"c0": "value"}}}
    
    res = client._generate_mock_response(state, questions)
    assert isinstance(res, MockSystemOneResult)
    assert "c0" in res.choices
    assert res.choices["c0"].choice == "c0"
    assert res.choices["c0"].probabilities["c0"] == 0.92


def test_generate_mock_noul():
    client = mock_jev_client()
    state = {"test": "state"}
    questions = {"noul": {"criteria": {}}}
    
    res = client._generate_mock_response(state, questions)
    assert isinstance(res, MockSystemOneResult)
    assert "noul" in res.nouls
    assert res.nouls["noul"].noul == 0.88


async def test_jev_decide_success(mock_jev_client):
    state = {"test": "state"}
    questions = {"c0": {"criteria": {"c0": "value"}}}
    
    res, latency = await mock_jev_client.decide(state, questions)
    assert isinstance(res, MockSystemOneResult)
    assert latency > 0