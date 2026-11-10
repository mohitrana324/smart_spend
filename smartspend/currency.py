"""Synchronous and asynchronous exchange-rate lookup helpers."""

import asyncio
import logging
import math
from typing import Any, Dict, Iterable, Tuple

import aiohttp
import requests

from smartspend.exceptions import CurrencyError
from smartspend.utils import retry, timer

LOGGER = logging.getLogger("smartspend")
API_URL = "https://open.er-api.com/v6/latest/{base}"
_RATE_CACHE: Dict[Tuple[str, str], float] = {}


def _currency_code(value: str) -> str:
    """Normalize and validate a three-letter currency code."""
    code = value.strip().upper()
    if len(code) != 3 or not code.isalpha():
        raise ValueError("Currency codes must contain three letters.")
    return code


def _validated_rate(payload: Any, target: str) -> float:
    """Extract a finite, positive target rate from an API response."""
    if not isinstance(payload, dict) or payload.get("result") != "success":
        raise CurrencyError("Exchange-rate service returned an invalid response.")
    rates = payload.get("rates")
    rate = rates.get(target) if isinstance(rates, dict) else None
    if isinstance(rate, bool) or not isinstance(rate, (int, float)):
        raise CurrencyError(f"No valid exchange rate was returned for {target}.")
    if not math.isfinite(float(rate)) or rate <= 0:
        raise CurrencyError(f"No valid exchange rate was returned for {target}.")
    return float(rate)


@timer
@retry(max_attempts=3, delay=1)
def _request_rate(base: str, target: str) -> float:
    """Fetch and validate one rate from the public synchronous API."""
    response = requests.get(API_URL.format(base=base), timeout=5)
    response.raise_for_status()
    return _validated_rate(response.json(), target)


def get_rate(base: str, target: str) -> float:
    """Return a live exchange rate or a previously cached rate on failure."""
    base_code = _currency_code(base)
    target_code = _currency_code(target)
    if base_code == target_code:
        return 1.0
    key = (base_code, target_code)
    try:
        rate = _request_rate(base_code, target_code)
    except (requests.RequestException, CurrencyError, ValueError, TypeError) as error:
        cached_rate = _RATE_CACHE.get(key)
        if cached_rate is None:
            raise CurrencyError(
                f"Could not get {base_code}/{target_code} exchange rate: {error}"
            ) from error
        LOGGER.warning("Using cached %s/%s exchange rate after API failure.", *key)
        return cached_rate
    _RATE_CACHE[key] = rate
    return rate


async def _request_rate_async(
    session: aiohttp.ClientSession, base: str, target: str
) -> float:
    """Fetch and validate one rate using an existing aiohttp session."""
    timeout = aiohttp.ClientTimeout(total=5)
    async with session.get(API_URL.format(base=base), timeout=timeout) as response:
        response.raise_for_status()
        payload = await response.json()
    return _validated_rate(payload, target)


async def get_rates_async(base: str, targets: Iterable[str]) -> Dict[str, float]:
    """Fetch multiple rates concurrently, using cached values for failures."""
    base_code = _currency_code(base)
    target_codes = [_currency_code(target) for target in targets]
    if not target_codes:
        return {}
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            *(
                _request_rate_async(session, base_code, target)
                for target in target_codes
            ),
            return_exceptions=True,
        )

    rates: Dict[str, float] = {}
    for target, result in zip(target_codes, results):
        key = (base_code, target)
        if isinstance(result, BaseException):
            cached_rate = _RATE_CACHE.get(key)
            if cached_rate is None:
                raise CurrencyError(
                    f"Could not get {base_code}/{target} exchange rate: {result}"
                ) from result
            LOGGER.warning("Using cached %s/%s exchange rate after API failure.", *key)
            rates[target] = cached_rate
        else:
            rates[target] = result
            _RATE_CACHE[key] = result
    return rates
