"""Domain exceptions raised by SmartSpend."""


class SmartSpendError(Exception):
    """Base exception for expected SmartSpend domain errors."""


class ExpenseNotFoundError(SmartSpendError):
    """Raised when an expense ID is not present in an expense book."""


class InvalidAmountError(SmartSpendError, ValueError):
    """Raised when an expense amount is not a finite positive number."""


class StorageError(SmartSpendError):
    """Raised when expense data cannot be read from or written to storage."""


class CurrencyError(SmartSpendError):
    """Raised when an exchange rate cannot be fetched or validated."""


class BudgetExceededError(SmartSpendError):
    """Raised when spending for a category and month exceeds its budget."""

    def __init__(
        self, category: str, month: str, budget: float, attempted_total: float
    ) -> None:
        self.category = category
        self.month = month
        self.budget = budget
        self.attempted_total = attempted_total
        super().__init__(
            f"{category} budget exceeded for {month}: "
            f"{attempted_total:.2f} spent, budget is {budget:.2f}."
        )
