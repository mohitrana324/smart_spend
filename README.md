# SmartSpend

SmartSpend is a Python command-line personal expense tracker. It stores expenses and category budgets in JSON, creates a timestamped backup before each save, exports CSV, and reports spending by month or category. Currency reports use live exchange rates when available and a cached rate as a fallback.

## Install

Python 3.8 or newer is required.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install -r requirements.txt
```

The editable install provides the `smartspend` command. The source checkout can also be run with `python -m smartspend.cli`.

## Usage

```sh
smartspend add --amount 250 --category Food --desc "Lunch" --tags work,lunch
smartspend list --category Food --month 2026-11 --page 1 --page-size 20
smartspend report --type monthly
smartspend report --type monthly --currency USD
smartspend report --type category
smartspend export --format csv --output report.csv
smartspend budget set --category Food --limit 5000
smartspend update --id 1 --amount 275 --desc "Team lunch"
smartspend delete --id 1
```

The default JSON file is `data/expenses.json`, logs go to `logs/smartspend.log`, and backups are written under `data/backups/`. Use global `--data-file` and `--log-file` options before the command to select alternate paths:

```sh
smartspend --data-file /tmp/expenses.json --log-file /tmp/smartspend.log list
```

Stored amounts are in INR. Currency conversion fetches a rate from the public ExchangeRate-API endpoint; successful rates are cached in memory for fallback during the current process. The asynchronous API is available to Python callers:

```python
import asyncio
from smartspend.currency import get_rates_async

rates = asyncio.run(get_rates_async("INR", ["USD", "EUR", "JPY"]))
print(rates)
```

## Architecture

- `smartspend.cli` parses commands, loads the expense book, executes an operation, and saves only when data changes.
- `smartspend.models` contains validated dataclasses, category budgets, and the transaction-capable `ExpenseBook`.
- `smartspend.storage` provides JSON persistence with atomic writes and backups, a structural `Storage` protocol, and CSV export.
- `smartspend.reports` calculates category and monthly totals; report calls are timed.
- `smartspend.currency` provides synchronous and asynchronous rate lookup with validation, retries, and cached fallback.
- `smartspend.logger` configures console and rotating-file logging.

## Development

```sh
python -m pytest --cov=smartspend --cov-report=term-missing
python -m black --check smartspend tests
python -m ruff check smartspend tests
python -m mypy smartspend/
```

Currency tests use mocked HTTP clients and do not require a network connection.
