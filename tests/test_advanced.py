"""Tests for SmartSpend's advanced Python utilities and context managers."""

import csv
import logging
import tempfile
import unittest
from pathlib import Path

from smartspend.models import Expense, ExpenseBook
from smartspend.reports import monthly_summary
from smartspend.storage import JsonStorage, Storage, atomic_write
from smartspend.utils import (
    compare_filter_memory,
    filter_expenses,
    get_month_key,
    iter_large_csv,
    log_calls,
    paginate,
    retry,
    timer,
)


class DecoratorTests(unittest.TestCase):
    """Verify retry behavior and wrapped-function metadata and logging."""

    def test_timer_and_log_calls_preserve_metadata(self) -> None:
        @timer
        @log_calls
        def sample(value: int) -> int:
            """Return the supplied value."""
            return value

        self.assertEqual(sample.__name__, "sample")
        self.assertEqual(sample.__doc__, "Return the supplied value.")
        with self.assertLogs("smartspend", level=logging.INFO) as captured:
            self.assertEqual(sample(4), 4)
        self.assertTrue(any("Calling" in message for message in captured.output))
        self.assertTrue(any("completed in" in message for message in captured.output))

    def test_retry_retries_and_preserves_metadata(self) -> None:
        attempts = 0

        def flaky() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise OSError("temporary failure")
            return "ready"

        retried = retry(max_attempts=3, delay=0)(flaky)
        self.assertEqual(retried(), "ready")
        self.assertEqual(attempts, 3)
        self.assertEqual(retried.__name__, "flaky")

    def test_retry_stops_at_attempt_limit(self) -> None:
        attempts = 0

        def always_fails() -> None:
            nonlocal attempts
            attempts += 1
            raise OSError("failure")

        with self.assertRaises(OSError):
            retry(max_attempts=2, delay=0)(always_fails)()
        self.assertEqual(attempts, 2)


class GeneratorAndReportTests(unittest.TestCase):
    """Verify lazy filtering, CSV streaming, pagination, and memory sizing."""

    def test_filter_is_lazy_and_pagination_selects_page(self) -> None:
        records = [
            Expense(index, 1, "Food", str(index), "2026-11-01") for index in range(1, 8)
        ]
        filtered = filter_expenses(records, category="food")

        self.assertEqual(iter(filtered), filtered)
        self.assertEqual(
            [expense.id for expense in paginate(filtered, 2, 3)], [4, 5, 6]
        )
        with self.assertRaises(ValueError):
            list(paginate(records, 0, 3))

    def test_large_csv_is_streamed_row_by_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.csv"
            with path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=("id", "category"))
                writer.writeheader()
                writer.writerows(
                    {"id": str(index), "category": "Food"} for index in range(3)
                )

            rows = iter_large_csv(path)
            self.assertEqual(next(rows), {"id": "0", "category": "Food"})
            self.assertEqual(len(list(rows)), 2)

    def test_generator_uses_less_result_container_memory_than_list(self) -> None:
        expenses = [
            Expense(index, 1, "Food", "Item", "2026-11-01") for index in range(1000)
        ]

        list_size, generator_size = compare_filter_memory(expenses, category="Food")

        self.assertGreater(list_size, generator_size)

    def test_cached_month_helper_and_grouped_report(self) -> None:
        get_month_key.cache_clear()
        self.assertEqual(get_month_key("2026-11-10"), "2026-11")
        get_month_key("2026-11-10")
        self.assertEqual(get_month_key.cache_info().hits, 1)
        book = ExpenseBook(
            [
                Expense(1, 2, "Food", "Tea", "2026-11-01"),
                Expense(2, 3, "Food", "Lunch", "2026-11-02"),
                Expense(3, 5, "Bills", "Rent", "2026-12-01"),
            ]
        )
        self.assertEqual(monthly_summary(book), {"2026-11": 5.0, "2026-12": 5.0})


class ContextManagerTests(unittest.TestCase):
    """Verify book rollback and atomic file replacement behavior."""

    def test_transaction_rolls_back_expenses_and_budgets(self) -> None:
        book = ExpenseBook([Expense(1, 5, "Food", "Lunch", "2026-11-01")])
        book.set_category_budget("Food", 20)

        with self.assertRaises(RuntimeError):
            with book.transaction():
                book.add(Expense(2, 5, "Food", "Snack", "2026-11-02"))
                book.set_category_budget("Food", 30)
                raise RuntimeError("rollback")

        self.assertEqual([expense.id for expense in book], [1])
        self.assertEqual(book.category_budgets, {"Food": 20.0})

    def test_atomic_write_keeps_existing_file_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            path.write_text("original", encoding="utf-8")

            with self.assertRaises(RuntimeError):
                with atomic_write(path) as output:
                    output.write("partial")
                    raise RuntimeError("write failed")

            self.assertEqual(path.read_text(encoding="utf-8"), "original")
            self.assertEqual(list(Path(directory).glob(".data.json.*.tmp")), [])

    def test_atomic_write_replaces_target_and_storage_protocol_is_satisfied(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            with atomic_write(path) as output:
                output.write("complete")

            self.assertEqual(path.read_text(encoding="utf-8"), "complete")
            self.assertIsInstance(JsonStorage(path), Storage)


if __name__ == "__main__":
    unittest.main()
