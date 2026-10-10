import asyncio
import time
from typing import Any
from pydantic import BaseModel
from src.app.config import Settings
from src.app.clients.breaker import Breaker


class JevUnavailable(Exception):
    """Exception raised when Jev service is unreachable, timed out, or circuit broken."""

    pass


class MockChoiceResult(BaseModel):
    choice: str
    probabilities: dict[str, float]


class MockNoulResult(BaseModel):
    noul: float  # probability of True/yes


class MockSystemOneResult(BaseModel):
    choices: dict[str, MockChoiceResult] = {}
    nouls: dict[str, MockNoulResult] = {}


class JevClient:

    def __init__(self, settings: Settings, breaker: Breaker):
        self._settings = settings
        self._breaker = breaker
        self._model = settings.jev_model
        self._timeout = settings.jev_timeout_s

        api_key = settings.typesafe_api_key.get_secret_value()
        self._is_mock = (
            not api_key or api_key.startswith("ts_test_") or settings.env == "dev"
        )

        if not self._is_mock:
            try:
                from typesafe_sdk import AsyncTypeSafeClient

                kw: dict[str, Any] = {
                    "api_key": api_key,
                    "model": self._model,
                }
                if settings.jev_base_url:
                    kw["base_url"] = settings.jev_base_url
                self._client = AsyncTypeSafeClient(**kw)
            except Exception:
                self._is_mock = True
                self._client = None
        else:
            self._client = None

    async def decide(
        self, state: dict[str, Any], questions: dict[str, Any]
    ) -> tuple[Any, int]:
        """Call Jev system_one for bounded decision making.

        Returns (result, latency_ms).
        """
        if self._breaker.open:
            raise JevUnavailable("Circuit breaker open for Jev client")

        t0 = time.perf_counter()

        if self._is_mock or self._client is None:
            # Deterministic mock response generation for development and tests
            res = self._generate_mock_response(state, questions)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            self._breaker.record_success(latency_ms / 1000.0)
            return res, latency_ms

        try:
            r = await asyncio.wait_for(
                self._client.system_one(state, questions), timeout=self._timeout
            )
            latency_ms = int((time.perf_counter() - t0) * 1000)
            self._breaker.record_success(latency_ms / 1000.0)
            return r, latency_ms
        except Exception as e:
            self._breaker.record_failure()
            raise JevUnavailable(
                f"Jev API call failed or timed out: {e}"
            ) from e

    def _generate_mock_response(
        self, state: dict[str, Any], questions: dict[str, Any]
    ) -> MockSystemOneResult:
        choices: dict[str, MockChoiceResult] = {}
        nouls: dict[str, MockNoulResult] = {}

        for k, q in questions.items():
            # If question has criteria (Choice)
            if hasattr(q, "criteria") and getattr(q, "criteria"):
                keys = list(q.criteria.keys())
                # Pick c0 if present, else first non-none
                winning = (
                    "c0"
                    if "c0" in keys
                    else (keys[0] if keys else "none")
                )
                probs = {}
                n = len(keys)
                if n > 0:
                    probs[winning] = 0.92
                    rem = 0.08 / max(1, n - 1)
                    for key in keys:
                        if key != winning:
                            probs[key] = round(rem, 4)
                else:
                    winning = "none"
                    probs = {"none": 1.0}
                choices[k] = MockChoiceResult(
                    choice=winning, probabilities=probs
                )
            # If Noul question
            else:
                nouls[k] = MockNoulResult(noul=0.88)

        return MockSystemOneResult(choices=choices, nouls=nouls)
