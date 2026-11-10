"""Reusable expense filtering, decorators, and display utilities."""

import csv
import logging
import sys
import time
from functools import lru_cache, wraps
from itertools import islice
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from smartspend.validators import validate_date

Expense = TypeVar("Expense")
Function = TypeVar("Function", bound=Callable[..., Any])
PathValue = Union[str, Path]
LOGGER = logging.getLogger("smartspend")


def timer(function: Function) -> Function:
    """Log execution time while preserving the wrapped function's metadata."""

    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            LOGGER.info(
                "%s completed in %.6f seconds",
                function.__qualname__,
                time.perf_counter() - started,
            )

    return cast(Function, wrapper)


def log_calls(function: Function) -> Function:
    """Log calls and failures while preserving the wrapped function's metadata."""

    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        LOGGER.info("Calling %s", function.__qualname__)
        try:
            result = function(*args, **kwargs)
        except Exception:
            LOGGER.exception("%s failed", function.__qualname__)
            raise
        LOGGER.info("%s completed", function.__qualname__)
        return result

    return cast(Function, wrapper)


def retry(max_attempts: int = 3, delay: float = 1.0) -> Callable[[Function], Function]:
    """Retry a function after exceptions, waiting ``delay`` between attempts."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least one")
    if delay < 0:
        raise ValueError("delay cannot be negative")

    def decorate(function: Function) -> Function:
        @wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, max_attempts + 1):
                try:
                    return function(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts:
                        raise
                    LOGGER.warning(
                        "%s failed on attempt %s/%s; retrying",
                        function.__qualname__,
                        attempt,
                        max_attempts,
                    )
                    time.sleep(delay)
            raise RuntimeError("Retry loop ended unexpectedly")

        return cast(Function, wrapper)

    return decorate


@lru_cache(maxsize=256)
def get_month_key(date_str: str) -> str:
    """Return the YYYY-MM key for a valid ISO date, cached by input string."""
    return validate_date(date_str)[:7]


def _matches_value(actual: Any, expected: Any) -> bool:
    """Compare values case-insensitively when strings or tag lists are used."""
    if isinstance(actual, str) and isinstance(expected, str):
        return actual.casefold() == expected.casefold()
    if isinstance(actual, list) and isinstance(expected, str):
        return any(
            isinstance(item, str) and item.casefold() == expected.casefold()
            for item in actual
        )
    return actual == expected


def _field_value(expense: Any, field: str) -> Any:
    """Read a field from either a model object or a dictionary record."""
    if isinstance(expense, dict):
        return expense.get(field)
    return getattr(expense, field, None)


def filter_expenses(expenses: Iterable[Expense], **criteria: Any) -> Iterator[Expense]:
    """Yield expenses matching every supplied field criterion lazily.

    String fields and individual tags are compared case-insensitively.
    """
    return (
        expense
        for expense in expenses
        if all(
            _matches_value(_field_value(expense, field), expected)
            for field, expected in criteria.items()
        )
    )


def paginate(items: Iterable[Expense], page: int, page_size: int) -> Iterator[Expense]:
    """Yield one 1-based page from an iterable without materializing earlier pages."""
    if page < 1 or page_size < 1:
        raise ValueError("page and page_size must be positive integers")
    start = (page - 1) * page_size
    return islice(items, start, start + page_size)


def iter_large_csv(path: PathValue) -> Iterator[Dict[str, str]]:
    """Stream CSV rows as dictionaries instead of loading the whole file."""
    with Path(path).open("r", newline="", encoding="utf-8") as csv_file:
        yield from csv.DictReader(csv_file)


def compare_filter_memory(
    expenses: Iterable[Expense], **criteria: Any
) -> Tuple[int, int]:
    """Return shallow list-result and lazy-generator sizes in bytes.

    The input records are shared; the comparison measures only the memory used
    to hold filtered results, not the expense objects themselves.
    """
    records = list(expenses)
    list_result = list(filter_expenses(records, **criteria))
    generator_result = filter_expenses(records, **criteria)
    return sys.getsizeof(list_result), sys.getsizeof(generator_result)


def format_currency(amount: float, symbol: str = "₹", decimals: int = 2) -> str:
    """Format an amount with a currency symbol and configurable precision."""
    return f"{symbol}{amount:,.{decimals}f}"
