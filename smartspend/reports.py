"""Procedural expense reports."""

from collections import Counter, defaultdict
from copy import deepcopy
from itertools import groupby
from typing import Dict, Iterable, List, Set, Tuple

from smartspend.models import BaseExpense
from smartspend.utils import timer


@timer
def category_totals(expenses: Iterable[BaseExpense]) -> Dict[str, float]:
    """Return the total amount spent in each category."""
    totals: Dict[str, float] = defaultdict(float)
    for expense in expenses:
        totals[expense.category] += expense.amount
    return dict(totals)


@timer
def top_expenses(expenses: Iterable[BaseExpense], limit: int = 3) -> List[BaseExpense]:
    """Return up to ``limit`` expenses, ordered by amount descending."""
    return sorted(expenses, key=lambda expense: expense.amount, reverse=True)[:limit]


@timer
def most_used_tags(expenses: Iterable[BaseExpense]) -> List[Tuple[str, int]]:
    """Return tags ordered by their usage count."""
    tags = Counter(tag.casefold() for expense in expenses for tag in expense.tags)
    return tags.most_common()


@timer
def unique_categories(expenses: Iterable[BaseExpense]) -> Set[str]:
    """Return the set of category names used by expenses."""
    return {expense.category for expense in expenses}


@timer
def monthly_summary(expenses: Iterable[BaseExpense]) -> Dict[str, float]:
    """Return total spending grouped by YYYY-MM."""
    records = sorted(expenses, key=lambda expense: expense.month)
    return {
        month: sum(expense.amount for expense in month_expenses)
        for month, month_expenses in groupby(records, key=lambda expense: expense.month)
    }


def copy_expenses(expenses: List[BaseExpense]) -> List[BaseExpense]:
    """Deep-copy expenses so nested tag lists are not shared."""
    return deepcopy(expenses)
