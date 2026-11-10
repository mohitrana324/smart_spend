"""Tests for SmartSpend domain models and their consumers."""

import unittest

from smartspend.exceptions import (
    BudgetExceededError,
    ExpenseNotFoundError,
    InvalidAmountError,
)
from smartspend.models import (
    BaseExpense,
    Category,
    Expense,
    ExpenseBook,
    RecurringExpense,
)
from smartspend.reports import (
    category_totals,
    monthly_summary,
    most_used_tags,
    top_expenses,
    unique_categories,
)
from smartspend.utils import filter_expenses
from smartspend.validators import validate_amount


class ExpenseModelTests(unittest.TestCase):
    """Verify expense construction, serialization, ordering, and recurrence."""

    def test_expense_round_trip_and_display(self) -> None:
        expense = Expense(1, 12.5, "Food", "Lunch", "2026-01-31", [" Work "])

        self.assertEqual(expense.month, "2026-01")
        self.assertEqual(expense.tags, ["Work"])
        self.assertEqual(Expense.from_dict(expense.to_dict()), expense)
        self.assertIn("Food", str(expense))
        self.assertIn("amount=12.5", repr(expense))

    def test_expenses_sort_by_amount(self) -> None:
        larger = Expense(1, 12.5, "Food", "Lunch", "2026-01-31")
        smaller = Expense(2, 2.0, "Food", "Tea", "2026-01-31")

        self.assertEqual(sorted([larger, smaller]), [smaller, larger])

    def test_invalid_amount_raises_custom_exception(self) -> None:
        with self.assertRaises(InvalidAmountError):
            Expense(1, 0, "Food", "Lunch", "2026-01-31")
        with self.assertRaises(ValueError):
            validate_amount("nan")

    def test_category_rejects_negative_budget(self) -> None:
        with self.assertRaises(ValueError):
            Category("Food", -1)

    def test_recurring_next_occurrences_and_mro(self) -> None:
        monthly = RecurringExpense(
            1, 5, "Bills", "Rent", "2026-01-31", frequency="monthly"
        )
        yearly = RecurringExpense(
            2, 5, "Bills", "Fee", "2024-02-29", frequency="yearly"
        )

        self.assertEqual(monthly.next_occurrence(), "2026-02-28")
        self.assertEqual(yearly.next_occurrence(), "2025-02-28")
        self.assertEqual(
            RecurringExpense.__mro__[:3], (RecurringExpense, Expense, BaseExpense)
        )


class ExpenseBookTests(unittest.TestCase):
    """Verify ExpenseBook collection behavior and monthly budget enforcement."""

    def setUp(self) -> None:
        self.book = ExpenseBook()
        self.book.set_category_budget("Food", 20)
        self.expense = Expense(1, 12.5, "Food", "Lunch", "2026-01-31", ["Work"])
        self.book.add(self.expense)

    def test_collection_methods(self) -> None:
        self.assertEqual(len(self.book), 1)
        self.assertIn(1, self.book)
        self.assertIn(self.expense, self.book)
        self.assertEqual(list(self.book), [self.expense])
        self.assertEqual(self.book.find(1), self.expense)
        self.assertEqual(self.book.remove(1), self.expense)
        self.assertEqual(len(self.book), 0)
        with self.assertRaises(ExpenseNotFoundError):
            self.book.find(1)

    def test_add_and_update_enforce_monthly_budget_atomically(self) -> None:
        with self.assertRaises(BudgetExceededError):
            self.book.add(Expense(2, 10, "Food", "Snack", "2026-01-15"))
        with self.assertRaises(BudgetExceededError):
            self.book.update(1, amount=21)
        self.assertEqual(self.book.find(1).amount, 12.5)

        with self.assertRaises(BudgetExceededError):
            self.book.set_category_budget("Food", 10)
        self.book.add(Expense(2, 7.5, "Food", "Snack", "2026-01-15"))
        self.assertEqual(len(self.book), 2)

    def test_reports_and_case_insensitive_filtering(self) -> None:
        self.book.add(Expense(2, 7.5, "Food", "Snack", "2026-01-15", ["home"]))

        self.assertEqual(category_totals(self.book), {"Food": 20.0})
        self.assertEqual(monthly_summary(self.book), {"2026-01": 20.0})
        self.assertEqual(most_used_tags(self.book), [("work", 1), ("home", 1)])
        self.assertEqual(unique_categories(self.book), {"Food"})
        self.assertEqual(top_expenses(self.book)[0].id, 1)
        self.assertEqual(
            list(filter_expenses(self.book, category="food", tags="WORK")),
            [self.expense],
        )


if __name__ == "__main__":
    unittest.main()
