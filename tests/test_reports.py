"""Parametrized report tests using a small expense-book fixture."""

from typing import Any, Dict

import pytest

from smartspend.models import Expense, ExpenseBook
from smartspend.reports import category_totals, monthly_summary


@pytest.fixture
def sample_book() -> ExpenseBook:
    """Return expenses covering two categories and two months."""
    return ExpenseBook(
        [
            Expense(1, 10, "Food", "Lunch", "2026-11-02"),
            Expense(2, 5, "Food", "Coffee", "2026-11-03"),
            Expense(3, 20, "Travel", "Train", "2026-12-01"),
        ]
    )


@pytest.mark.parametrize(
    ("report", "expected"),
    [
        (category_totals, {"Food": 15.0, "Travel": 20.0}),
        (monthly_summary, {"2026-11": 15.0, "2026-12": 20.0}),
    ],
)
def test_report_totals_are_correct(
    sample_book: ExpenseBook, report: Any, expected: Dict[str, float]
) -> None:
    """Known sample expenses produce deterministic report totals."""
    assert report(sample_book) == expected
