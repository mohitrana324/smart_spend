"""Domain models for expenses, categories, and expense collections."""

import calendar
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from math import isfinite
from types import TracebackType
from typing import Any, Dict, Iterable, Iterator, List, Literal, Optional, Tuple, Type

from smartspend.exceptions import (
    BudgetExceededError,
    ExpenseNotFoundError,
    InvalidAmountError,
)
from smartspend.validators import validate_category, validate_date
from smartspend.utils import log_calls


@dataclass
class BaseExpense(ABC):
    """Common validated fields shared by one-time and recurring expenses."""

    id: int
    amount: float
    category: str
    description: str
    date: str
    tags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Normalize and validate values at model construction."""
        try:
            self.amount = float(self.amount)
        except (TypeError, ValueError):
            raise InvalidAmountError("Amount must be greater than zero.") from None
        if not isfinite(self.amount) or self.amount <= 0:
            raise InvalidAmountError("Amount must be greater than zero.")
        self.category = validate_category(self.category)
        self.date = validate_date(self.date)
        self.tags = [tag.strip() for tag in self.tags if tag.strip()]

    @property
    def month(self) -> str:
        """Return the expense month in YYYY-MM format."""
        return self.date[:7]

    @abstractmethod
    def next_occurrence(self) -> Optional[str]:
        """Return the next occurrence date, if this expense recurs."""

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize the expense to a plain dictionary."""


@dataclass(repr=False)
class Expense(BaseExpense):
    """A single non-recurring expense."""

    def __lt__(self, other: object) -> bool:
        """Compare expenses by amount for ascending sorting."""
        if not isinstance(other, BaseExpense):
            return NotImplemented
        return self.amount < other.amount

    def __str__(self) -> str:
        """Return a readable one-line expense description."""
        return (
            f"Expense #{self.id}: ₹{self.amount:.2f} for {self.category} "
            f"on {self.date} ({self.description})"
        )

    def __repr__(self) -> str:
        """Return an informative representation for debugging."""
        return (
            f"Expense(id={self.id!r}, amount={self.amount!r}, "
            f"category={self.category!r}, description={self.description!r}, "
            f"date={self.date!r}, tags={self.tags!r})"
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Expense":
        """Build an expense from its serialized dictionary representation."""
        return cls(
            id=int(data["id"]),
            amount=float(data["amount"]),
            category=str(data["category"]),
            description=str(data["description"]),
            date=str(data["date"]),
            tags=list(data.get("tags", [])),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this expense to a plain dictionary."""
        return {
            "id": self.id,
            "amount": self.amount,
            "category": self.category,
            "description": self.description,
            "date": self.date,
            "tags": list(self.tags),
        }

    def next_occurrence(self) -> Optional[str]:
        """Return None because a one-time expense does not recur."""
        return None


@dataclass(repr=False)
class RecurringExpense(Expense):
    """An expense that repeats at a supported calendar frequency."""

    frequency: str = "monthly"

    def __post_init__(self) -> None:
        """Validate common expense fields and the recurrence frequency."""
        super().__post_init__()
        self.frequency = self.frequency.casefold()
        if self.frequency not in {"daily", "weekly", "monthly", "yearly"}:
            raise ValueError("Frequency must be daily, weekly, monthly, or yearly.")

    def __str__(self) -> str:
        """Return a readable description including recurrence frequency."""
        return f"{super().__str__()} (repeats {self.frequency})"

    def __repr__(self) -> str:
        """Return an informative representation including frequency."""
        return f"RecurringExpense({super().__repr__()}, frequency={self.frequency!r})"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this recurring expense, including its frequency."""
        data = super().to_dict()
        data["frequency"] = self.frequency
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecurringExpense":
        """Build a recurring expense from its serialized dictionary."""
        return cls(
            id=int(data["id"]),
            amount=float(data["amount"]),
            category=str(data["category"]),
            description=str(data["description"]),
            date=str(data["date"]),
            tags=list(data.get("tags", [])),
            frequency=str(data.get("frequency", "monthly")),
        )

    def next_occurrence(self) -> str:
        """Return the next recurrence date as an ISO-formatted string."""
        current = date.fromisoformat(self.date)
        if self.frequency == "daily":
            following = current + timedelta(days=1)
        elif self.frequency == "weekly":
            following = current + timedelta(weeks=1)
        elif self.frequency == "monthly":
            year, month = _next_month(current.year, current.month)
            day = min(current.day, calendar.monthrange(year, month)[1])
            following = date(year, month, day)
        else:
            year = current.year + 1
            day = min(current.day, calendar.monthrange(year, current.month)[1])
            following = date(year, current.month, day)
        return following.isoformat()


def _next_month(year: int, month: int) -> Tuple[int, int]:
    """Return the calendar year and month following the supplied month."""
    return (year + 1, 1) if month == 12 else (year, month + 1)


class Category:
    """A spending category with an optional non-negative monthly budget."""

    def __init__(self, name: str, budget: Optional[float] = None) -> None:
        """Create a category and validate its optional monthly budget."""
        self.name = validate_category(name)
        self._budget: Optional[float] = None
        self.budget = budget

    @property
    def budget(self) -> Optional[float]:
        """Return this category's monthly budget, if one is set."""
        return self._budget

    @budget.setter
    def budget(self, value: Optional[float]) -> None:
        """Set a finite, non-negative monthly budget or clear it with None."""
        if value is None:
            self._budget = None
            return
        try:
            amount = float(value)
        except (TypeError, ValueError):
            raise ValueError("Budget must be a non-negative number.") from None
        if not isfinite(amount) or amount < 0:
            raise ValueError("Budget must be a non-negative number.")
        self._budget = amount


class ExpenseBook:
    """Manage expenses and enforce category budgets by calendar month."""

    def __init__(self, expenses: Optional[Iterable[BaseExpense]] = None) -> None:
        """Create a book and add any initial expenses through validation."""
        self._expenses: List[BaseExpense] = []
        self._categories: Dict[str, Category] = {}
        for expense in expenses or []:
            self.add(expense)

    @log_calls
    def add(self, expense: BaseExpense) -> None:
        """Add an expense unless its ID is duplicated or its budget is exceeded."""
        if any(existing.id == expense.id for existing in self._expenses):
            raise ValueError(f"Expense ID {expense.id} already exists.")
        self._check_budget(expense)
        self._expenses.append(expense)

    @log_calls
    def remove(self, expense_id: int) -> BaseExpense:
        """Remove and return the expense with the requested ID."""
        expense = self.find(expense_id)
        self._expenses.remove(expense)
        return expense

    @log_calls
    def update(self, expense_id: int, **changes: Any) -> BaseExpense:
        """Replace an expense with validated changes and recheck its budget."""
        current = self.find(expense_id)
        if "id" in changes and changes["id"] != expense_id:
            raise ValueError("Expense IDs cannot be changed.")
        updated = replace(current, **changes)
        self._check_budget(updated, ignore_id=expense_id)
        self._expenses[self._expenses.index(current)] = updated
        return updated

    def find(self, expense_id: int) -> BaseExpense:
        """Return an expense by ID or raise ExpenseNotFoundError."""
        for expense in self._expenses:
            if expense.id == expense_id:
                return expense
        raise ExpenseNotFoundError(f"Expense {expense_id} was not found.")

    @log_calls
    def set_category_budget(self, name: str, budget: Optional[float]) -> Category:
        """Set a category budget after checking existing monthly totals."""
        key = validate_category(name).casefold()
        category = Category(name, budget)
        if budget is not None:
            for month in {
                item.month for item in self._expenses if item.category.casefold() == key
            }:
                total = sum(
                    item.amount
                    for item in self._expenses
                    if item.category.casefold() == key and item.month == month
                )
                self._check_total(category.name, month, category.budget, total)
        self._categories[key] = category
        return category

    @property
    def category_budgets(self) -> Dict[str, float]:
        """Return configured category budgets keyed by category name."""
        return {
            category.name: category.budget
            for category in self._categories.values()
            if category.budget is not None
        }

    def transaction(self) -> "Transaction":
        """Return a context manager that rolls back book changes on failure."""
        return Transaction(self)

    def _check_budget(
        self, expense: BaseExpense, ignore_id: Optional[int] = None
    ) -> None:
        """Raise when adding an expense would exceed its monthly category budget."""
        category = self._categories.get(expense.category.casefold())
        if category is None or category.budget is None:
            return
        total = sum(
            item.amount
            for item in self._expenses
            if item.id != ignore_id
            and item.category.casefold() == expense.category.casefold()
            and item.month == expense.month
        )
        self._check_total(
            category.name, expense.month, category.budget, total + expense.amount
        )

    @staticmethod
    def _check_total(
        category: str, month: str, budget: Optional[float], total: float
    ) -> None:
        """Raise a detailed budget exception when a total is over its limit."""
        if budget is not None and total > budget:
            raise BudgetExceededError(category, month, budget, total)

    def __len__(self) -> int:
        """Return the number of expenses in the book."""
        return len(self._expenses)

    def __iter__(self) -> Iterator[BaseExpense]:
        """Yield expenses in insertion order."""
        yield from self._expenses

    def __contains__(self, item: object) -> bool:
        """Check membership by expense object or integer ID."""
        if isinstance(item, int):
            return any(expense.id == item for expense in self._expenses)
        return item in self._expenses


class Transaction:
    """Snapshot an ExpenseBook and restore it if a with-block fails."""

    def __init__(self, book: ExpenseBook) -> None:
        """Create a transaction for the supplied expense book."""
        self.book = book
        self._expenses: List[BaseExpense] = []
        self._categories: Dict[str, Category] = {}

    def __enter__(self) -> ExpenseBook:
        """Snapshot the book and return it for changes inside the with-block."""
        self._expenses = deepcopy(self.book._expenses)
        self._categories = deepcopy(self.book._categories)
        return self.book

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Literal[False]:
        """Restore the snapshot after an exception and let it propagate."""
        if exc_type is not None:
            self.book._expenses = self._expenses
            self.book._categories = self._categories
        return False
