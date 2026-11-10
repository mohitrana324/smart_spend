# SmartSpend -- 7-Day Python Training Project Plan

> **Purpose:** Use this document as the implementation brief for GitHub
> Copilot. Build one Python command-line application, **SmartSpend**,
> incrementally over seven days. Keep a single codebase and
> extend/refactor it each day rather than creating separate projects.

## Instructions for GitHub Copilot

Act as a senior Python engineer and mentor. Help implement the project
in small, reviewable steps.

1.  Follow the day-by-day scope in this document. Do not implement
    later-day features early unless they are needed to keep the current
    code working.
2.  Before making substantial changes, inspect the existing project and
    explain which files will be created or modified.
3.  Implement readable, maintainable Python code with PEP 8 naming,
    docstrings, and type hints as introduced in the plan.
4.  Do not leave core functionality as `pass`, TODOs, or pseudocode.
    Implement it and provide runnable examples.
5.  Validate inputs and handle expected errors with clear user-facing
    messages. Do not expose raw tracebacks for normal user errors.
6.  Add or update tests as features are introduced. Keep tests
    deterministic; mock external HTTP calls.
7.  Preserve existing working functionality when refactoring. Explain
    any breaking changes.
8.  After each task, provide:
    -   Files created/changed
    -   Commands to run
    -   Example input and expected output
    -   Tests to execute
    -   A short explanation of the Python concepts used
    -   A checklist showing which acceptance criteria are met
9.  Ask before making assumptions that materially change the
    requirements. Prefer the standard library unless a dependency is
    specified in this plan.
10. Do not claim a task is complete until the code has been run or the
    relevant tests have been executed.

------------------------------------------------------------------------

## 1. Project overview

**SmartSpend** is a personal expense tracker that runs from the command
line (CLI).

Users should be able to record expenses, categorize and tag them, set
budgets, generate reports, convert totals into other currencies using a
public exchange-rate API, and export their data.

### Final feature list (end of Day 7)

-   Add, list, update, and delete expenses with validation.
-   Categories, tags, and budgets with over-budget alerts.
-   Monthly and category reports, plus top-N spending analysis.
-   Persistent JSON storage and CSV export, with automatic backups.
-   Live currency conversion using a public exchange-rate API
    (synchronous and asynchronous).
-   Logging, custom exceptions, retry and timing decorators.
-   A pytest suite with mocks; type hints checked by mypy.
-   An installable Python package with README, `requirements.txt`, and
    Git history.

### Important scope notes

-   This is a **CLI application**, not a web application or React
    frontend.
-   The specified persistence mechanism is JSON and CSV files; a SQL
    database is not required.
-   Currency conversion is the external API integration in this plan.
-   Keep the same application and evolve it over the seven days.

------------------------------------------------------------------------

## 2. Target project structure

Build toward this structure by Day 7. It is not necessary to create
every file on Day 1; add files on the day specified.

``` text
smartspend/
├── smartspend/
│   ├── __init__.py
│   ├── cli.py              # Day 1 to Day 5; argparse CLI
│   ├── models.py           # Day 4
│   ├── storage.py          # Day 5
│   ├── reports.py          # Day 2 to Day 6
│   ├── validators.py       # Day 3
│   ├── utils.py            # Day 3 to Day 6
│   ├── exceptions.py       # Day 4
│   ├── currency.py         # Day 7
│   └── logger.py           # Day 5
├── tests/
│   ├── test_models.py
│   ├── test_storage.py
│   ├── test_reports.py
│   └── test_currency.py
├── data/
│   └── expenses.json
├── requirements.txt
├── pyproject.toml
├── README.md
└── .gitignore
```

------------------------------------------------------------------------

# 3. Day-by-day implementation plan

## Day 1 -- Project skeleton and interactive menu

**Goal:** Create a working, menu-driven expense tracker using Python
fundamentals. Store data in memory only for now.

### Concepts to learn and apply

-   Variables, data types, operators, and type conversion
-   `if` / `elif` / `else`
-   `while` loops, `break`, and `continue`
-   Strings, f-strings, `input()`, and `print()`
-   Basic input validation
-   Lists and tuples

### Tasks

1.  Create the project folder and a single `cli.py` file.
2.  Build a repeating menu:
    -   Add Expense
    -   View Expenses
    -   Total Spent
    -   Exit
3.  For Add Expense, ask for amount, category, and description.
4.  Validate that the amount is a positive number. If input is invalid,
    show a helpful message and ask again; do not crash.
5.  Temporarily store each expense as a tuple
    `(amount, category, description)` inside a list.
6.  View Expenses should print a neatly aligned table using f-string
    width specifiers.
7.  Total Spent should calculate the sum and display it with two decimal
    places and a currency symbol.

### Example menu

``` text
===== SmartSpend Expense Tracker =====
1. Add Expense
2. View Expenses
3. Total Spent
4. Exit

Enter your choice:
```

### Acceptance criteria

-   [ ] Invalid input does not crash the application.
-   [ ] The menu repeats until the user explicitly exits.
-   [ ] Expenses can be added and viewed during the current run.
-   [ ] Total spent is calculated correctly.
-   [ ] Output is aligned and readable.

**Expected milestone:** A working menu-driven CLI with in-memory
expenses.

------------------------------------------------------------------------

## Day 2 -- Data modelling with built-in structures and first reports

**Goal:** Improve expense records and add update, delete, search, and
reporting features.

### Concepts to learn and apply

-   Lists, dictionaries, sets, and tuples; when to use each
-   List and dictionary comprehensions
-   `sorted()` with `key`, `enumerate()`, and `zip()`
-   `collections.Counter` and `collections.defaultdict`
-   Shallow copy versus deep copy

### Tasks

1.  Replace each expense tuple with a dictionary containing:
    -   `id`
    -   `amount`
    -   `category`
    -   `description`
    -   `date`
    -   `tags`
2.  Generate expense IDs incrementally.
3.  Add menu options to update an expense, delete an expense, and search
    by category or tag.
4.  Create `reports.py` with procedural functions that return:
    -   Total per category using `defaultdict`
    -   Top 3 expenses using `sorted(..., key=...)`
    -   Most-used tags using `Counter`
    -   Unique categories using a set
5.  Add a monthly summary using a dictionary comprehension keyed by
    `YYYY-MM`.
6.  Demonstrate how shallow copying the expenses list can cause a
    nested-data mutation bug, then fix it with `copy.deepcopy`.
7.  Make category and tag searches case-insensitive.

### Acceptance criteria

-   [ ] Each expense has a unique incremental ID.
-   [ ] Update, delete, and search work correctly.
-   [ ] Category totals, top 3 expenses, most-used tags, and unique
    categories are correct.
-   [ ] Monthly summary is grouped by `YYYY-MM`.
-   [ ] Search is case-insensitive.
-   [ ] The shallow-copy issue and deep-copy solution can be explained.

**Expected milestone:** Expense management and first category/monthly
reports.

------------------------------------------------------------------------

## Day 3 -- Functions, modules, packages, and environment

**Goal:** Refactor the code into a maintainable Python package and
reusable functions.

### Concepts to learn and apply

-   Functions, default arguments, keyword arguments, `*args`, and
    `**kwargs`
-   Scope and LEGB rule, closures, lambdas
-   `map()`, `filter()`, and `reduce()`
-   Modules, packages, `__init__.py`, and `if __name__ == "__main__"`
-   Virtual environments, pip, and `requirements.txt`
-   PEP 8, docstrings, and type hints

### Tasks

1.  Convert the project into the `smartspend/` package with:
    -   `cli.py`
    -   `reports.py`
    -   `validators.py`
    -   `utils.py`
2.  Move input validation into `validators.py`:
    -   `validate_amount`
    -   `validate_category`
    -   `validate_date`
    -   `parse_tags`
3.  Write `filter_expenses(expenses, **criteria)` in `utils.py`. It
    should filter by any combination of supplied fields.
4.  Write `format_currency(amount, symbol="₹", decimals=2)` using
    default arguments.
5.  Add docstrings and type hints to every function.
6.  Create and use a virtual environment.
7.  Add development tools such as Black and Ruff to `requirements.txt`.
8.  Run Black and Ruff and fix reported issues.
9.  Ensure the app can be launched with `python -m smartspend.cli`.

### Acceptance criteria

-   [ ] The package structure is in place.
-   [ ] `python -m smartspend.cli` runs the application.
-   [ ] Validation logic is separated into `validators.py`.
-   [ ] Filtering supports multiple criteria through `**kwargs`.
-   [ ] Functions have docstrings and type hints.
-   [ ] No function is longer than approximately 25 lines where
    reasonably practical.
-   [ ] Black and Ruff report no issues.

**Expected milestone:** A structured Python package with reusable,
documented functions.

------------------------------------------------------------------------

## Day 4 -- Object-oriented redesign

**Goal:** Replace raw dictionaries and procedural data handling with
classes and domain models.

### Concepts to learn and apply

-   Classes, objects, `__init__`, instance/class/static methods
-   Inheritance, `super()`, and abstract base classes
-   `@property` with validation and `@dataclass`
-   Dunder methods: `__str__`, `__repr__`, `__eq__`, `__lt__`,
    `__len__`, `__iter__`
-   Custom exception hierarchy
-   Method Resolution Order (MRO)

### Tasks

1.  Create `models.py`.
2.  Implement an `Expense` dataclass with fields:
    -   `id`
    -   `amount`
    -   `category`
    -   `description`
    -   `date`
    -   `tags`
3.  Add to `Expense`:
    -   `__lt__` to sort expenses by amount
    -   A `month` property returning `YYYY-MM`
    -   `from_dict()` class method
    -   `to_dict()` instance method
    -   Meaningful `__str__` and `__repr__`
4.  Implement a `Category` class. Its budget property must reject
    negative values.
5.  Implement an `ExpenseBook` class to hold expenses, with:
    -   `add`
    -   `remove`
    -   `update`
    -   `find`
    -   `__len__`
    -   `__iter__`
    -   `__contains__`
6.  Create `exceptions.py` with:
    -   `SmartSpendError` as the base exception
    -   `ExpenseNotFoundError`
    -   `InvalidAmountError`
    -   `BudgetExceededError`
7.  Add recurring expenses using an abstract `BaseExpense` and
    subclasses `Expense` and `RecurringExpense`. `RecurringExpense`
    should include a frequency and `next_occurrence()` method.
8.  Refactor `cli.py` and `reports.py` to use the new classes instead of
    raw dictionaries.
9.  Raise `BudgetExceededError` when a category's monthly total crosses
    its budget. Catch it in the CLI and display a warning.

### Acceptance criteria

-   [ ] Expenses are represented by the `Expense` model.
-   [ ] `ExpenseBook` supports add, remove, update, find, iteration,
    length, and containment.
-   [ ] `print(expense)` and `repr(expense)` produce meaningful output.
-   [ ] Negative category budgets are rejected.
-   [ ] Custom exceptions are raised and handled appropriately.
-   [ ] Recurring expense behavior is implemented.
-   [ ] The developer can explain the MRO for `RecurringExpense`.

**Expected milestone:** A class-based expense tracker with domain models
and custom exceptions.

------------------------------------------------------------------------

## Day 5 -- Persistence, error handling, logging, and real CLI

**Goal:** Persist data to files and replace the interactive menu with
command-line arguments.

### Concepts to learn and apply

-   File I/O using `with`
-   `json`, `csv`, `pathlib`, and `shutil`
-   `try` / `except` / `else` / `finally`
-   Exception chaining with `raise ... from ...`
-   Logging, including console and rotating file handlers
-   `datetime` and `argparse`

### Tasks

1.  Create `storage.py` with a `JsonStorage` class:
    -   `save(book)`
    -   `load()` returning an `ExpenseBook`
2.  Before every save, create an automatic backup in `data/backups/`
    named `expenses_<timestamp>.json`.
3.  Add a `CsvExporter` class with `export(book, path)`.
4.  Handle `PermissionError`, `FileNotFoundError`, and
    `json.JSONDecodeError` gracefully with user-friendly messages.
5.  Create `logger.py` and configure console logging plus a rotating
    file handler.
6.  Replace diagnostic `print()` calls with logging:
    -   INFO for normal actions
    -   WARNING for budget alerts
    -   ERROR for failures
7.  Replace the interactive menu with an `argparse` CLI supporting
    commands equivalent to:

``` bash
smartspend add --amount 250 --category Food --desc "Lunch" --tags work,lunch

smartspend list --category Food --month 2026-11

smartspend report --type monthly

smartspend export --format csv --output report.csv

smartspend budget set --category Food --limit 5000
```

8.  Load the expense book when a command starts.
9.  Save the expense book after every command that changes data.
10. Use `datetime` to default the expense date to today and validate
    user-supplied dates.

### Acceptance criteria

-   [ ] Data survives application restarts.
-   [ ] JSON storage can save and load an `ExpenseBook`.
-   [ ] A timestamped backup is created before every save.
-   [ ] CSV export works.
-   [ ] Corrupted JSON produces a clear message rather than an unhandled
    traceback.
-   [ ] Log file is created and rotates.
-   [ ] CLI commands and arguments work as specified.
-   [ ] Mutating commands save data; read-only commands do not
    unnecessarily modify it.

**Expected milestone:** A persistent, file-backed application with an
argparse CLI, backups, CSV export, and logging.

------------------------------------------------------------------------

## Day 6 -- Advanced Python: decorators, generators, context managers, and typing

**Goal:** Apply advanced Python features to real application
requirements.

### Concepts to learn and apply

-   Iterators and generators, generator expressions, and lazy evaluation
-   Decorators with and without arguments
-   `functools.wraps` and `lru_cache`
-   Class-based context managers and `contextlib`
-   `itertools` and `functools.partial`
-   Typing: `Optional`, `Protocol`, `TypedDict`, and generics
-   Mypy

### Tasks

1.  Add decorators in `utils.py`:
    -   `@timer` on report functions
    -   `@log_calls` on all mutating `ExpenseBook` methods
    -   `@retry(max_attempts=3, delay=1)` for use with Day 7 API calls
    -   `@lru_cache` on a pure helper such as `get_month_key(date_str)`
2.  Use `functools.wraps` so decorated functions preserve metadata such
    as `__name__` and `__doc__`.
3.  Convert `ExpenseBook.__iter__` and report filters into generators
    where appropriate.
4.  Add `iter_large_csv(path)` to stream a large CSV file line by line.
5.  Demonstrate memory savings by comparing the generator approach with
    a list-based approach.
6.  Write a `Transaction()` context manager for `ExpenseBook`. It must
    roll back changes if an exception occurs inside the `with` block.
7.  Write an `atomic_write(path)` context manager for JSON storage.
    Write to a temporary file and rename it only after the write
    succeeds.
8.  Use `itertools.groupby` for a grouped-by-month report.
9.  Use `itertools.islice` for paginated list output.
10. Define a `Storage` Protocol so `JsonStorage` and a future
    `SqliteStorage` can be interchangeable.
11. Add complete type hints and make `mypy smartspend/` pass cleanly.

### Acceptance criteria

-   [ ] Decorators work and preserve function metadata.
-   [ ] Timing and method-call logging are demonstrated.
-   [ ] Retry decorator supports configurable attempts and delay.
-   [ ] Generator-based CSV reading works line by line.
-   [ ] Generator versus list memory usage is demonstrated.
-   [ ] Transaction rollback is demonstrated with a test or runnable
    example.
-   [ ] Atomic writes avoid leaving partially written target files.
-   [ ] Monthly grouping and pagination work.
-   [ ] Mypy reports zero errors for `smartspend/`.

**Expected milestone:** Advanced Python features integrated into working
application code.

------------------------------------------------------------------------

## Day 7 -- External API, async, testing, and packaging

**Goal:** Integrate currency conversion, complete automated tests, and
make the package installable.

### Concepts to learn and apply

-   HTTP requests, status codes, timeouts, and JSON parsing
-   `asyncio`, `async` / `await`, `asyncio.gather`, and `aiohttp`
-   Pytest fixtures and parametrization
-   `tmp_path`, `unittest.mock`, and `monkeypatch`
-   Python packaging with `pyproject.toml`
-   Console entry points and Git basics

### Tasks

1.  Create `currency.py`.
2.  Implement synchronous `get_rate(base, target)`:
    -   Call a free public exchange-rate API using `requests`.
    -   Use the `@retry` and `@timer` decorators.
    -   Set a 5-second timeout.
    -   Handle HTTP errors, timeouts, and invalid API responses.
    -   Use a fallback cached rate if the API call fails, where a cached
        rate is available.
3.  Implement asynchronous `get_rates_async(base, targets)`:
    -   Fetch several currency rates concurrently.
    -   Use `asyncio.gather`.
    -   Use `aiohttp` for asynchronous HTTP requests.
4.  Add a CLI report command supporting currency conversion, for
    example:

``` bash
smartspend report --type monthly --currency USD
```

5.  Create tests in `tests/`:
    -   `test_models.py`: valid/invalid amounts, equality, and sorting
    -   `test_storage.py`: save/load using `tmp_path`, and backup
        verification
    -   `test_reports.py`: known input data produces expected totals
    -   `test_currency.py`: mock HTTP calls so tests never require a
        live network
6.  Use pytest parametrization for multiple input cases.
7.  Target at least 80% test coverage using `pytest --cov`.
8.  Add `pyproject.toml` with a console-script entry point so
    `pip install -e .` makes the `smartspend` command available.
9.  Write `README.md` containing installation instructions, usage
    examples, and an architecture overview.
10. Initialize Git, create `.gitignore`, and commit changes in logical
    steps.
11. Push to a repository and open a pull request for review, if
    repository access and permissions are available.

### Acceptance criteria

-   [ ] `pip install -e .` completes successfully in a fresh
    environment.
-   [ ] `smartspend --help` works after installation.
-   [ ] Currency conversion works with a live API when available.
-   [ ] API failures are handled with retry and fallback behavior where
    a cached rate exists.
-   [ ] Async currency fetching works for multiple targets.
-   [ ] All tests pass offline because API calls are mocked.
-   [ ] Test coverage is at least 80%.
-   [ ] The async version is measurably faster than sequential requests
    for 5 or more currencies under a controlled test/demo.
-   [ ] README includes setup, usage, and architecture details.
-   [ ] Git history contains meaningful commits; a pull request is
    opened if possible.

**Expected milestone:** A tested, documented, installable SmartSpend
Python package.

------------------------------------------------------------------------

# 4. Concept coverage map

  -----------------------------------------------------------------------
  Python area                         Where it is applied
  ----------------------------------- -----------------------------------
  Syntax, data types, control flow,   Day 1: menu, input, validation, and
  and strings                         tables

  Data structures and comprehensions  Day 2: expense records and reports

  Functions, modules, packages, venv, Day 3: project refactoring
  and PEP 8                           

  OOP, dataclasses, ABCs, dunder      Day 4: domain models
  methods, and exceptions             

  Files, JSON/CSV, pathlib, logging,  Day 5: storage and CLI
  argparse, and datetime              

  Generators, decorators, context     Day 6: utilities and transactions
  managers, typing, and itertools     

  HTTP, asyncio, pytest, mocking,     Day 7: currency, tests, and release
  packaging, and Git                  
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 5. Daily review format

At the end of each day, prepare for this review:

1.  **Demo -- 10 minutes:** Run the commands or features added that day.
2.  **Code walkthrough -- 15 minutes:** Explain how the code works and
    why each concept or design choice was used.
3.  **Refactor challenge -- 5 minutes:** Review one piece of code and
    explain how it could be improved using that day's concepts.

Do not move to the next day until the current day's acceptance criteria
have been checked and the application still runs.

------------------------------------------------------------------------

# 6. Evaluation rubric

  Criterion                                    Marks
  ----------------------------------------- --------
  Correctness and completeness of tasks            4
  Code quality (PEP 8, naming, structure)          2
  Appropriate use of the day's concepts            2
  Error handling and edge cases                    1
  Ability to explain the code in review            1
  **Total per day**                           **10**

------------------------------------------------------------------------

# 7. Final delivery checklist

-   [ ] Working SmartSpend CLI installable via pip.
-   [ ] Add, list, update, delete, search, category, tag, and budget
    features.
-   [ ] JSON persistence with automatic backups.
-   [ ] CSV export.
-   [ ] Monthly/category reports and top-N analysis.
-   [ ] Live and asynchronous currency conversion with retry and
    fallback behavior.
-   [ ] Logging and custom exceptions.
-   [ ] Decorators and context managers used in the application.
-   [ ] Pytest suite with at least 80% coverage; API calls mocked.
-   [ ] Mypy, Black, and Ruff pass without errors.
-   [ ] README contains setup and usage instructions.
-   [ ] Git repository has meaningful commit history and a pull request,
    if repository access permits.

------------------------------------------------------------------------

## 8. Suggested way to work with Copilot

Use this document as the project specification. Then give Copilot one
focused instruction at a time, for example:

> "Read `SMARTSPEND_PLAN.md`. We are starting Day 1 only. Inspect the
> workspace, create the Day 1 project skeleton, and implement the
> interactive menu and required features. Do not implement Day 2 or
> later features. Explain each file and show me how to run and test it.
> Check every Day 1 acceptance criterion before finishing."

For each following day, ask Copilot to implement only that day's tasks,
first reviewing the current code and preserving existing functionality.
