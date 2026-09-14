"""Everything a command needs before it can value the account.

`cli.py` is command wiring: options, echoing, exit codes. This module holds
the domain-shaped half that three reviews flagged as living in the wrong
file -- where the files are, which currencies are in play, and how a seed
plus a transaction ledger become a replayable Portfolio.

It does raise `click.ClickException`, which is not a domain concept. That is
deliberate: these functions exist to serve the CLI, every failure they detect
is a user-facing precondition ("seed.yaml is missing"), and click is already
a hard dependency. Keeping the messages next to the checks beats scattering
half of each check across two modules.
"""

import os
from typing import List

import click

DEFAULT_ROOT = os.environ.get("NAV_ROOT", "subprojects/nav")
DEFAULT_HISTORICAL = "historical.parquet"

# The currency NAV is denominated in, and the one it is also reported in.
# `valuation.COLUMNS` has one fixed cash column for each; see
# `valuation.UnrepresentableCurrencyError`.
BASE_CURRENCY = "KRW"
REPORT_CURRENCY = "USD"


def paths(root: str) -> dict:
    return {
        "symbols": os.path.join(root, "symbols.yaml"),
        "categories": os.path.join(root, "categories.yaml"),
        "seed": os.path.join(root, "seed.yaml"),
        "transaction": os.path.join(root, "data", "transaction.parquet"),
        "nav_daily": os.path.join(root, "data", "nav_daily.parquet"),
    }


def load_state(root: str):
    """Everything needed to value the account: maps, seed, transactions."""
    from nav import categories, ingest, replay, seed as seed_module, symbols

    p = paths(root)
    symbol_map = symbols.load(p["symbols"])
    category_map = categories.load(p["categories"])
    account_seed = seed_module.load(p["seed"], symbol_map)

    frame = ingest.load_frame(p["transaction"])
    transactions = [] if frame is None else ingest.from_frame(frame)
    portfolio = replay.build_portfolio(
        account_seed, transactions, category_map, base_currency=BASE_CURRENCY
    )
    return p, symbol_map, account_seed, transactions, portfolio


def held_tickers(account_seed, transactions) -> List[str]:
    tickers = set(account_seed.positions)
    tickers |= {t.ticker for t in transactions if t.ticker}
    return sorted(tickers)


def read_historical(path: str):
    import pandas as pd

    return pd.read_parquet(path)
