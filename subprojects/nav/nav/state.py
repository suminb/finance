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


def require_file(path: str, what: str, hint: str) -> str:
    """A missing input file is a first-run certainty, not an exceptional case.

    Left to itself each of these exits on a bare FileNotFoundError traceback
    with nothing on stdout, which tells a first-time user neither which of the
    three files is missing nor what to put in it.
    """
    if not os.path.exists(path):
        raise click.ClickException("{} not found: {}. {}".format(what, path, hint))
    return path


def load_state(root: str):
    """Everything needed to value the account: maps, seed, transactions."""
    from nav import categories, ingest, replay, seed as seed_module, symbols

    p = paths(root)
    require_file(
        p["symbols"], "symbols.yaml", "It maps each 종목명 to a ticker and a currency."
    )
    require_file(
        p["categories"],
        "categories.yaml",
        "It maps each 거래종류 to a handler; `nav categories <export>` prints the "
        "vocabulary to fill it from.",
    )
    require_file(
        p["seed"],
        "seed.yaml",
        "It holds the opening 잔고 every later figure is replayed from. "
        "Copy {} and fill it in.".format(os.path.join(root, "seed.example.yaml")),
    )
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


def account_currencies(
    account_seed,
    transactions,
    symbol_map,
    base: str = BASE_CURRENCY,
    report: str = REPORT_CURRENCY,
) -> List[str]:
    """Every currency this account actually deals in.

    This was `extra_currencies=["USD"]`, hardcoded at four call sites, while
    the shipped symbols.yaml already carries `넥슨 일본 -> 3659.T, JPY`. A
    holding priced in an unlisted currency would have had no rate fetched and
    no rate in the price table, so it could not be valued at all.

    Derived instead from the data: the seed's cash keys, the currency of every
    row in the ledger (a 입금 in JPY creates a `_JPY` balance whether or not a
    JPY ticker is held), and the currency of every held ticker -- plus the base
    and reporting currencies, which are always needed.
    """
    currencies = {base, report}
    currencies |= set(account_seed.cash)
    currencies |= {t.currency for t in transactions if t.currency}
    for ticker in held_tickers(account_seed, transactions):
        try:
            currencies.add(symbol_map.currency_of(ticker))
        except KeyError:
            raise click.ClickException(
                "{} is held but is no longer listed in symbols.yaml, so its "
                "currency is unknown. Restore the entry, or rebuild after "
                "correcting it.".format(ticker)
            ) from None
    return sorted(currencies)


def read_historical(path: str):
    """The shared parquet price warehouse.

    Absent, pyarrow raises its own error about a path it was handed, which
    says nothing about what creates the file.
    """
    import pandas as pd

    if not os.path.exists(path):
        raise click.ClickException(
            "No price history at {}. `nav sync` creates it by fetching closes "
            "and FX from Yahoo; `--historical PATH` points at another "
            "warehouse.".format(path)
        )
    return pd.read_parquet(path)
