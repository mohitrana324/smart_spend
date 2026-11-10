"""Input validation helpers for SmartSpend."""

from datetime import datetime
from math import isfinite
from typing import List, Union


def validate_amount(value: Union[str, float]) -> float:
    """Return a positive numeric amount or raise a helpful ValueError."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        raise ValueError("Enter a valid amount greater than zero.") from None
    if not isfinite(amount) or amount <= 0:
        raise ValueError("Enter a valid amount greater than zero.")
    return amount


def validate_category(value: str) -> str:
    """Strip and return a non-empty category name."""
    category = value.strip()
    if not category:
        raise ValueError("Category cannot be empty.")
    return category


def validate_date(value: str) -> str:
    """Validate a YYYY-MM-DD date and return its ISO-formatted value."""
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise ValueError("Enter a valid date in YYYY-MM-DD format.") from None


def parse_tags(value: str) -> List[str]:
    """Parse comma-separated tags, dropping empty entries."""
    return [tag.strip() for tag in value.split(",") if tag.strip()]
