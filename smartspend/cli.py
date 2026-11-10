"""Argument-driven command-line interface for SmartSpend."""

import argparse
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Sequence

from smartspend.currency import get_rate
from smartspend.exceptions import BudgetExceededError, SmartSpendError
from smartspend.logger import configure_logger
from smartspend.models import Expense, ExpenseBook
from smartspend.reports import category_totals, monthly_summary
from smartspend.storage import CsvExporter, JsonStorage
from smartspend.utils import filter_expenses, format_currency, paginate
from smartspend.validators import (
    parse_tags,
    validate_amount,
    validate_category,
    validate_date,
)


def _date_argument(value: str) -> str:
    """Validate a CLI date and convert errors to argparse messages."""
    try:
        return validate_date(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def _month_argument(value: str) -> str:
    """Validate a month in YYYY-MM format."""
    try:
        return datetime.strptime(value, "%Y-%m").strftime("%Y-%m")
    except ValueError as error:
        raise argparse.ArgumentTypeError("Month must use YYYY-MM format.") from error


def _positive_int(value: str) -> int:
    """Parse a positive integer argument for list pagination."""
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Value must be a positive integer.") from error
    if number < 1:
        raise argparse.ArgumentTypeError("Value must be a positive integer.")
    return number


def _currency_argument(value: str) -> str:
    """Normalize a three-letter currency code for report conversion."""
    code = value.strip().upper()
    if len(code) != 3 or not code.isascii() or not code.isalpha():
        raise argparse.ArgumentTypeError("Currency codes must contain three letters.")
    return code


def _budget_argument(value: str) -> float:
    """Parse a finite, non-negative budget amount."""
    try:
        budget = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Budget must be a non-negative number."
        ) from error
    if budget < 0 or budget != budget or budget in (float("inf"), float("-inf")):
        raise argparse.ArgumentTypeError("Budget must be a non-negative number.")
    return budget


def build_parser() -> argparse.ArgumentParser:
    """Build the SmartSpend command and option parser."""
    parser = argparse.ArgumentParser(prog="smartspend")
    parser.add_argument("--data-file", type=Path, default=Path("data/expenses.json"))
    parser.add_argument("--log-file", type=Path, default=Path("logs/smartspend.log"))
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="record an expense")
    add.add_argument("--amount", type=validate_amount, required=True)
    add.add_argument("--category", type=validate_category, required=True)
    add.add_argument("--desc", required=True)
    add.add_argument("--tags", type=parse_tags, default=[])
    add.add_argument("--date", type=_date_argument)

    update = commands.add_parser("update", help="update an expense")
    update.add_argument("--id", type=int, required=True)
    update.add_argument("--amount", type=validate_amount)
    update.add_argument("--category", type=validate_category)
    update.add_argument("--desc")
    update.add_argument("--tags", type=parse_tags)
    update.add_argument("--date", type=_date_argument)

    delete = commands.add_parser("delete", help="delete an expense")
    delete.add_argument("--id", type=int, required=True)

    listing = commands.add_parser("list", help="list recorded expenses")
    listing.add_argument("--category", type=validate_category)
    listing.add_argument("--month", type=_month_argument)
    listing.add_argument("--page", type=_positive_int, default=1)
    listing.add_argument("--page-size", type=_positive_int, default=20)

    report = commands.add_parser("report", help="show spending reports")
    report.add_argument("--type", choices=("monthly", "category"), required=True)
    report.add_argument("--currency", type=_currency_argument)

    export = commands.add_parser("export", help="export expenses")
    export.add_argument("--format", choices=("csv",), required=True)
    export.add_argument("--output", type=Path, required=True)

    budget = commands.add_parser("budget", help="manage category budgets")
    budget_commands = budget.add_subparsers(dest="budget_command", required=True)
    set_budget = budget_commands.add_parser("set", help="set a monthly budget")
    set_budget.add_argument("--category", type=validate_category, required=True)
    set_budget.add_argument("--limit", type=_budget_argument, required=True)
    return parser


def _print_expenses(
    book: ExpenseBook,
    category: Optional[str],
    month: Optional[str],
    page: int,
    page_size: int,
) -> None:
    """Print expenses matching any supplied list filters."""
    criteria = {}
    if category:
        criteria["category"] = category
    if month:
        criteria["month"] = month
    expenses = list(paginate(filter_expenses(book, **criteria), page, page_size))
    if not expenses:
        print("No expenses found.")
        return
    print(
        f"{'ID':>4}  {'Amount':>12}  {'Category':<16}  {'Date':<10}  Description  Tags"
    )
    for expense in expenses:
        print(
            f"{expense.id:>4}  {format_currency(expense.amount):>12}  "
            f"{expense.category:<16}  {expense.date:<10}  "
            f"{expense.description}  {', '.join(expense.tags)}"
        )


def _run_command(
    args: argparse.Namespace, book: ExpenseBook, logger: logging.Logger
) -> bool:
    """Run a parsed command and return whether the book was changed."""
    if args.command == "add":
        expense = Expense(
            id=max((item.id for item in book), default=0) + 1,
            amount=args.amount,
            category=args.category,
            description=args.desc,
            date=args.date or date.today().isoformat(),
            tags=args.tags,
        )
        try:
            book.add(expense)
        except BudgetExceededError as error:
            logger.warning("%s", error)
            return False
        logger.info("Added expense %s (%s).", expense.id, expense.category)
        return True

    if args.command == "update":
        changes = {
            key: value
            for key, value in {
                "amount": args.amount,
                "category": args.category,
                "description": args.desc,
                "tags": args.tags,
                "date": args.date,
            }.items()
            if value is not None
        }
        if not changes:
            logger.info("No fields supplied; expense was not changed.")
            return False
        try:
            book.update(args.id, **changes)
        except BudgetExceededError as error:
            logger.warning("%s", error)
            return False
        logger.info("Updated expense %s.", args.id)
        return True

    if args.command == "delete":
        book.remove(args.id)
        logger.info("Deleted expense %s.", args.id)
        return True

    if args.command == "list":
        _print_expenses(book, args.category, args.month, args.page, args.page_size)
        logger.info("Listed expenses.")
        return False

    if args.command == "report":
        rate = get_rate("INR", args.currency) if args.currency else None
        if args.type == "monthly":
            totals = sorted(monthly_summary(book).items())
        else:
            totals = sorted(category_totals(book).items())
        for label, total in totals:
            if rate is None:
                print(f"{label}: {format_currency(total)}")
            else:
                converted = format_currency(total * rate, symbol=f"{args.currency} ")
                print(f"{label}: {format_currency(total)} = {converted}")
        logger.info("Generated %s report.", args.type)
        return False

    if args.command == "export":
        output = CsvExporter().export(book, args.output)
        logger.info("Exported CSV to %s.", output)
        return False

    if args.command == "budget" and args.budget_command == "set":
        try:
            book.set_category_budget(args.category, args.limit)
        except BudgetExceededError as error:
            logger.warning("%s", error)
            return False
        logger.info("Set %s monthly budget to %s.", args.category, args.limit)
        return True

    raise SmartSpendError("Unsupported command.")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Load data, run one CLI command, and persist successful changes."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        logger = configure_logger(args.log_file)
    except OSError as error:
        logging.basicConfig(level=logging.ERROR)
        logging.getLogger("smartspend").error("Could not configure logging: %s", error)
        return 1

    storage = JsonStorage(args.data_file)
    try:
        book = storage.load()
        changed = _run_command(args, book, logger)
        if changed:
            storage.save(book)
    except SmartSpendError as error:
        logger.error("%s", error)
        return 1
    logger.info("Command completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
