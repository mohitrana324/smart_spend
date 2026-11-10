"""Tests for SmartSpend persistence, export, and rotating logging."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from smartspend.exceptions import StorageError
from smartspend.logger import configure_logger
from smartspend.models import Expense, ExpenseBook, RecurringExpense
from smartspend.storage import CsvExporter, JsonStorage


class JsonStorageTests(unittest.TestCase):
    """Verify JSON round-trips, missing files, corruption, and backups."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.path = self.directory / "expenses.json"
        self.storage = JsonStorage(self.path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_round_trip_budgets_recurring_expenses_and_backups(self) -> None:
        book = ExpenseBook()
        book.set_category_budget("Food", 500)
        book.add(Expense(1, 25, "Food", "Lunch", "2026-11-10", ["work"]))
        book.add(
            RecurringExpense(
                2, 100, "Bills", "Internet", "2026-11-01", frequency="monthly"
            )
        )

        first_backup = self.storage.save(book)
        self.assertTrue(first_backup.is_file())
        self.assertRegex(first_backup.name, r"^expenses_\d{8}_\d{6}_\d{6}\.json$")
        loaded = self.storage.load()
        recurring = loaded.find(2)
        self.assertIsInstance(recurring, RecurringExpense)
        self.assertEqual(recurring.frequency, "monthly")
        self.assertEqual(loaded.category_budgets, {"Food": 500.0})

        book.add(Expense(3, 10, "Food", "Tea", "2026-11-10"))
        second_backup = self.storage.save(book)
        with second_backup.open(encoding="utf-8") as backup_file:
            backed_up_payload = json.load(backup_file)
        self.assertEqual(len(backed_up_payload["expenses"]), 2)

    def test_missing_file_loads_empty_book(self) -> None:
        self.assertEqual(len(self.storage.load()), 0)

    def test_corrupted_json_has_friendly_storage_error(self) -> None:
        self.path.write_text("{not valid json", encoding="utf-8")

        with self.assertRaisesRegex(StorageError, "contains invalid JSON"):
            self.storage.load()

    def test_csv_export_writes_expense_fields(self) -> None:
        book = ExpenseBook(
            [Expense(1, 25, "Food", "Lunch", "2026-11-10", ["work", "meal"])]
        )
        output = self.directory / "report.csv"

        self.assertEqual(CsvExporter().export(book, output), output)
        with output.open(newline="", encoding="utf-8") as csv_file:
            rows = list(csv.DictReader(csv_file))
        self.assertEqual(rows[0]["category"], "Food")
        self.assertEqual(rows[0]["tags"], "work,meal")
        self.assertEqual(rows[0]["frequency"], "")

    def test_csv_missing_directory_has_friendly_error(self) -> None:
        book = ExpenseBook()

        with self.assertRaisesRegex(StorageError, "Could not find a directory"):
            CsvExporter().export(book, self.directory / "missing" / "report.csv")


class LoggerTests(unittest.TestCase):
    """Verify console/file logging and rotating file behavior."""

    def test_logger_creates_and_rotates_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "logs" / "smartspend.log"
            logger = configure_logger(path, max_bytes=100, backup_count=2)
            for index in range(10):
                logger.info("message %s %s", index, "x" * 40)

            self.assertTrue(path.is_file())
            self.assertTrue(Path(str(path) + ".1").is_file())
