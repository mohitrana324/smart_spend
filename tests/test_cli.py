"""Tests for the argument-driven SmartSpend CLI."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from smartspend.cli import main
from smartspend.storage import JsonStorage


class SmartSpendCliTests(unittest.TestCase):
    """Verify command persistence, filtering, and user-facing failures."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.data_path = self.directory / "expenses.json"
        self.log_path = self.directory / "logs" / "smartspend.log"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _run(self, *arguments: str) -> int:
        """Run a command using isolated data and log files."""
        return main(
            [
                "--data-file",
                str(self.data_path),
                "--log-file",
                str(self.log_path),
                *arguments,
            ]
        )

    def test_commands_persist_data_and_read_only_commands_do_not_save(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(
                self._run(
                    "add",
                    "--amount",
                    "250",
                    "--category",
                    "Food",
                    "--desc",
                    "Lunch",
                    "--tags",
                    "work,lunch",
                    "--date",
                    "2026-11-10",
                ),
                0,
            )

        loaded = JsonStorage(self.data_path).load()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded.find(1).category, "Food")
        backups_before_read = list((self.directory / "backups").glob("*.json"))
        saved_content = self.data_path.read_text(encoding="utf-8")

        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(
            io.StringIO()
        ):
            self.assertEqual(
                self._run("list", "--category", "Food", "--month", "2026-11"), 0
            )
            self.assertEqual(self._run("report", "--type", "monthly"), 0)
            self.assertEqual(
                self._run(
                    "export",
                    "--format",
                    "csv",
                    "--output",
                    str(self.directory / "report.csv"),
                ),
                0,
            )

        self.assertEqual(self.data_path.read_text(encoding="utf-8"), saved_content)
        self.assertEqual(
            list((self.directory / "backups").glob("*.json")), backups_before_read
        )

    def test_corrupt_json_is_logged_without_traceback(self) -> None:
        self.data_path.write_text("not json", encoding="utf-8")
        errors = io.StringIO()

        with contextlib.redirect_stderr(errors):
            result = self._run("list")

        self.assertEqual(result, 1)
        self.assertIn("contains invalid JSON", errors.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())

    def test_update_and_delete_commands_persist(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(
                self._run(
                    "add",
                    "--amount",
                    "25",
                    "--category",
                    "Food",
                    "--desc",
                    "Lunch",
                    "--date",
                    "2026-11-10",
                ),
                0,
            )
            self.assertEqual(
                self._run(
                    "update", "--id", "1", "--amount", "30", "--desc", "Late lunch"
                ),
                0,
            )
            self.assertEqual(self._run("delete", "--id", "1"), 0)

        self.assertEqual(len(JsonStorage(self.data_path).load()), 0)
        self.assertEqual(len(list((self.directory / "backups").glob("*.json"))), 3)

    def test_budget_alert_does_not_save_rejected_expense(self) -> None:
        logs = io.StringIO()
        with contextlib.redirect_stderr(logs):
            self.assertEqual(
                self._run("budget", "set", "--category", "Food", "--limit", "20"),
                0,
            )
            self.assertEqual(
                self._run(
                    "add",
                    "--amount",
                    "25",
                    "--category",
                    "Food",
                    "--desc",
                    "Lunch",
                    "--date",
                    "2026-11-10",
                ),
                0,
            )

        book = JsonStorage(self.data_path).load()
        self.assertEqual(len(book), 0)
        self.assertEqual(book.category_budgets, {"Food": 20.0})
        self.assertIn("WARNING", logs.getvalue())
