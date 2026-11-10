"""JSON persistence and CSV export for SmartSpend."""

import csv
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, IO, Iterator, Optional, Protocol, Union, runtime_checkable

from smartspend.exceptions import SmartSpendError, StorageError
from smartspend.models import Expense, ExpenseBook, RecurringExpense

PathValue = Union[str, Path]


@runtime_checkable
class Storage(Protocol):
    """Interface for interchangeable expense-book storage backends."""

    def save(self, book: ExpenseBook) -> Path:
        """Persist an expense book."""

    def load(self) -> ExpenseBook:
        """Load an expense book."""


@contextmanager
def atomic_write(path: PathValue) -> Iterator[IO[str]]:
    """Write a temporary file beside the target, replacing it only on success."""
    target = Path(path)
    temporary_path: Optional[Path] = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(
            dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp"
        )
        temporary_path = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as temporary_file:
            yield temporary_file
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(str(temporary_path), str(target))
    except BaseException:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
        raise


class JsonStorage:
    """Save and load an ExpenseBook as JSON with timestamped backups."""

    def __init__(
        self,
        path: PathValue = "data/expenses.json",
        backup_dir: Optional[PathValue] = None,
    ) -> None:
        """Configure the JSON file and its backup directory."""
        self.path = Path(path)
        self.backup_dir = (
            Path(backup_dir) if backup_dir else self.path.parent / "backups"
        )

    def save(self, book: ExpenseBook) -> Path:
        """Back up the current state and save the supplied expense book."""
        payload = self._serialize(book)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            backup = self._create_backup(payload)
            with atomic_write(self.path) as json_file:
                json.dump(payload, json_file, indent=2, ensure_ascii=False)
                json_file.write("\n")
            return backup
        except PermissionError as error:
            raise StorageError(
                f"Permission denied while saving {self.path}."
            ) from error
        except FileNotFoundError as error:
            raise StorageError(
                f"Could not find a directory for {self.path}."
            ) from error
        except OSError as error:
            raise StorageError(
                f"Could not save expense data to {self.path}: {error}"
            ) from error

    def load(self) -> ExpenseBook:
        """Load an ExpenseBook, returning an empty book if the file is absent."""
        try:
            with self.path.open("r", encoding="utf-8") as json_file:
                payload = json.load(json_file)
        except FileNotFoundError:
            return ExpenseBook()
        except PermissionError as error:
            raise StorageError(
                f"Permission denied while reading {self.path}."
            ) from error
        except json.JSONDecodeError as error:
            raise StorageError(
                f"Data file {self.path} contains invalid JSON."
            ) from error
        except OSError as error:
            raise StorageError(
                f"Could not read expense data from {self.path}: {error}"
            ) from error

        try:
            return self._deserialize(payload)
        except (KeyError, TypeError, ValueError, SmartSpendError) as error:
            raise StorageError(
                f"Data file {self.path} has an invalid expense format."
            ) from error

    def _create_backup(self, payload: Dict[str, Any]) -> Path:
        """Copy the existing file or save an initial snapshot before each write."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup = self.backup_dir / f"expenses_{timestamp}.json"
        if self.path.exists():
            shutil.copy2(self.path, backup)
        else:
            with backup.open("w", encoding="utf-8") as backup_file:
                json.dump(payload, backup_file, indent=2, ensure_ascii=False)
                backup_file.write("\n")
        return backup

    @staticmethod
    def _serialize(book: ExpenseBook) -> Dict[str, Any]:
        """Convert a book and its configured budgets to JSON-compatible data."""
        return {
            "expenses": [expense.to_dict() for expense in book],
            "budgets": book.category_budgets,
        }

    @staticmethod
    def _deserialize(payload: Any) -> ExpenseBook:
        """Build a validated ExpenseBook from current or legacy JSON data."""
        if isinstance(payload, list):
            expense_data = payload
            budgets: Dict[str, float] = {}
        elif isinstance(payload, dict):
            expense_data = payload.get("expenses", [])
            budgets = payload.get("budgets", {})
        else:
            raise ValueError("The top-level JSON value must be an object or list.")
        if not isinstance(expense_data, list) or not isinstance(budgets, dict):
            raise ValueError("Expenses must be a list and budgets must be an object.")

        book = ExpenseBook()
        for category, budget in budgets.items():
            book.set_category_budget(str(category), float(budget))
        for item in expense_data:
            if not isinstance(item, dict):
                raise ValueError("Each expense must be a JSON object.")
            expense_type = RecurringExpense if "frequency" in item else Expense
            book.add(expense_type.from_dict(item))
        return book


class CsvExporter:
    """Export expenses to a UTF-8 CSV file."""

    FIELDS = ("id", "amount", "category", "description", "date", "tags", "frequency")

    def export(self, book: ExpenseBook, path: PathValue) -> Path:
        """Write expenses to CSV and return the output path."""
        output_path = Path(path)
        try:
            with output_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=self.FIELDS)
                writer.writeheader()
                for expense in book:
                    row = expense.to_dict()
                    row["tags"] = ",".join(row["tags"])
                    row["frequency"] = getattr(expense, "frequency", "")
                    writer.writerow(row)
            return output_path
        except PermissionError as error:
            raise StorageError(
                f"Permission denied while writing {output_path}."
            ) from error
        except FileNotFoundError as error:
            raise StorageError(
                f"Could not find a directory for {output_path}."
            ) from error
        except OSError as error:
            raise StorageError(
                f"Could not export CSV to {output_path}: {error}"
            ) from error
