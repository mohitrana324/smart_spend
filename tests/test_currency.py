"""Offline tests for synchronous and asynchronous currency conversion."""

import asyncio
import time
from typing import Any, Dict, Optional
from unittest.mock import Mock

import pytest
import requests

from smartspend import currency
from smartspend.cli import main
from smartspend.exceptions import CurrencyError
from smartspend.models import Expense, ExpenseBook
from smartspend.storage import JsonStorage


@pytest.fixture(autouse=True)
def clear_rate_cache() -> None:
    """Keep cached-rate behavior isolated between tests."""
    currency._RATE_CACHE.clear()
    yield
    currency._RATE_CACHE.clear()


@pytest.mark.parametrize(
    ("target", "rate"),
    [("USD", 0.012), ("EUR", 0.011), ("JPY", 1.8)],
)
def test_get_rate_uses_validated_api_response(
    monkeypatch: pytest.MonkeyPatch, target: str, rate: float
) -> None:
    response = Mock()
    response.json.return_value = {"result": "success", "rates": {target: rate}}
    request = Mock(return_value=response)
    monkeypatch.setattr(currency.requests, "get", request)

    assert currency.get_rate("inr", target.lower()) == rate
    request.assert_called_once_with(currency.API_URL.format(base="INR"), timeout=5)


def test_get_rate_uses_cached_rate_after_retrying_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    currency._RATE_CACHE[("INR", "USD")] = 0.012
    request = Mock(side_effect=requests.Timeout("offline"))
    monkeypatch.setattr(currency.requests, "get", request)
    monkeypatch.setattr("smartspend.utils.time.sleep", lambda _: None)

    assert currency.get_rate("INR", "USD") == 0.012
    assert request.call_count == 3


def test_get_rate_reports_failure_without_cached_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = Mock(side_effect=requests.ConnectionError("offline"))
    monkeypatch.setattr(currency.requests, "get", request)
    monkeypatch.setattr("smartspend.utils.time.sleep", lambda _: None)

    with pytest.raises(CurrencyError, match="Could not get INR/USD"):
        currency.get_rate("INR", "USD")
    assert request.call_count == 3


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {"result": "error", "rates": {"USD": 0.5}},
        {"result": "success", "rates": {"USD": "bad"}},
        {"result": "success", "rates": {"USD": 0}},
    ],
)
def test_invalid_api_response_raises_currency_error(
    monkeypatch: pytest.MonkeyPatch, payload: Any
) -> None:
    response = Mock()
    response.json.return_value = payload
    monkeypatch.setattr(currency.requests, "get", Mock(return_value=response))
    monkeypatch.setattr("smartspend.utils.time.sleep", lambda _: None)

    with pytest.raises(CurrencyError):
        currency.get_rate("INR", "USD")


class _Concurrency:
    """Track simultaneous fake HTTP responses for the async timing test."""

    active = 0
    maximum = 0


class _FakeResponse:
    def __init__(
        self,
        payload: Dict[str, Any],
        delay: float,
        state: _Concurrency,
        error: Optional[Exception] = None,
    ) -> None:
        self.payload = payload
        self.delay = delay
        self.state = state
        self.error = error

    async def __aenter__(self) -> "_FakeResponse":
        self.state.active += 1
        self.state.maximum = max(self.state.maximum, self.state.active)
        await asyncio.sleep(self.delay)
        self.state.active -= 1
        if self.error is not None:
            raise self.error
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def json(self) -> Dict[str, Any]:
        return self.payload


class _FakeSession:
    def __init__(
        self,
        payload: Dict[str, Any],
        delay: float,
        state: _Concurrency,
        error: Optional[Exception] = None,
    ) -> None:
        self.payload = payload
        self.delay = delay
        self.state = state
        self.error = error

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    def get(self, url: str, timeout: Optional[Any] = None) -> _FakeResponse:
        return _FakeResponse(self.payload, self.delay, self.state, self.error)


def test_async_rates_run_concurrently_and_cache_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    targets = ["USD", "EUR", "JPY", "CAD", "AUD"]
    delay = 0.04
    state = _Concurrency()
    payload = {
        "result": "success",
        "rates": {target: index + 0.5 for index, target in enumerate(targets)},
    }
    monkeypatch.setattr(
        currency.aiohttp,
        "ClientSession",
        lambda: _FakeSession(payload, delay, state),
    )
    started = time.perf_counter()
    rates = asyncio.run(currency.get_rates_async("INR", targets))
    concurrent_duration = time.perf_counter() - started

    assert rates == payload["rates"]
    assert state.maximum == len(targets)
    assert concurrent_duration < len(targets) * delay * 0.75
    assert currency._RATE_CACHE[("INR", "USD")] == 0.5


def test_async_rates_use_cache_on_failure_and_error_without_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _Concurrency()
    monkeypatch.setattr(
        currency.aiohttp,
        "ClientSession",
        lambda: _FakeSession({}, 0, state, RuntimeError("offline")),
    )
    currency._RATE_CACHE[("INR", "USD")] = 0.012

    assert asyncio.run(currency.get_rates_async("INR", ["USD"])) == {"USD": 0.012}
    currency._RATE_CACHE.clear()
    with pytest.raises(CurrencyError, match="Could not get INR/USD"):
        asyncio.run(currency.get_rates_async("INR", ["USD"]))


def test_cli_report_converts_totals_with_mocked_rate(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    data_path = tmp_path / "expenses.json"
    log_path = tmp_path / "smartspend.log"
    JsonStorage(data_path).save(
        ExpenseBook([Expense(1, 250, "Food", "Lunch", "2026-11-10")])
    )
    monkeypatch.setattr("smartspend.cli.get_rate", lambda base, target: 0.012)

    result = main(
        [
            "--data-file",
            str(data_path),
            "--log-file",
            str(log_path),
            "report",
            "--type",
            "monthly",
            "--currency",
            "usd",
        ]
    )

    assert result == 0
    assert "2026-11: ₹250.00 = USD 3.00" in capsys.readouterr().out
