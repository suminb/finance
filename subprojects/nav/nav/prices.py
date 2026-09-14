"""Daily closes and FX, expressed in one base currency.

An exchange rate is just another symbol in the parquet warehouse, so FX needs
no separate fetching, caching or storage path.
"""

import os
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

from nav.model import cash_ticker
from nav.symbols import SymbolMap


class NoPriceHistoryError(Exception):
    pass


def fx_symbol(currency: str, base: str) -> Optional[str]:
    """Warehouse symbol for a currency's rate against the base currency."""
    if currency == base:
        return None
    return "{}{}=X".format(currency, base)


def region_for(symbol: str) -> str:
    if symbol.endswith("=X"):
        return "FX"
    if symbol.endswith((".KS", ".KQ")):
        return "KR"
    return "US"


def required_symbols(
    tickers: Iterable[str],
    symbol_map: SymbolMap,
    base: str,
    extra_currencies: Iterable[str] = (),
) -> List[str]:
    """Every warehouse symbol needed to value these holdings."""
    needed = set()
    currencies = set(extra_currencies)
    for ticker in tickers:
        needed.add(ticker)
        currencies.add(symbol_map.currency_of(ticker))
    for currency in currencies:
        symbol = fx_symbol(currency, base)
        if symbol:
            needed.add(symbol)
    return sorted(needed)


DEFAULT_DELAY_FACTOR = 2.0

# `finance.ext.warehouse.fetch_historical_data`'s own default. Named here
# because it bounds how far back a NAV series can start: a seed_date older
# than this has no closes to value its opening positions against, and the
# failure surfaces much later, as _as_of's "No close for X at or before ...".
FETCH_PERIOD = "5y"


def refresh(
    symbols_to_fetch: Iterable[str],
    historical_path: str,
    delay_factor: float = DEFAULT_DELAY_FACTOR,
) -> pd.DataFrame:
    """Fetches each symbol's history and merges it into the warehouse file.

    Each symbol is refetched in full (`period="5y"`) and the warehouse
    deduplicates on (date, region, symbol) afterwards; nothing here works out
    which dates are already held. That is wasteful but self-healing -- a
    revised or backfilled close replaces the stored one -- and at the scale of
    one personal account it costs seconds.

    It does mean one yfinance call per held symbol per `nav sync`, so calls
    are spaced by up to `delay_factor` seconds, matching
    `finance.ext.warehouse.refresh_tickers_and_historical_data`. Pass
    `delay_factor=0` to disable the wait (tests, or a single symbol).
    """
    import random
    import time

    from finance.ext.warehouse import concat_dataframes, fetch_historical_data

    existing = (
        pd.read_parquet(historical_path) if os.path.exists(historical_path) else None
    )
    for index, symbol in enumerate(symbols_to_fetch):
        if index and delay_factor:
            time.sleep(random.random() * delay_factor)
        fetched = fetch_historical_data(
            symbol, region=region_for(symbol), period=FETCH_PERIOD
        )
        existing = fetched if existing is None else concat_dataframes(existing, fetched)

    if existing is None:
        raise ValueError("No symbols to refresh")

    os.makedirs(os.path.dirname(os.path.abspath(historical_path)), exist_ok=True)
    existing.to_parquet(historical_path, index=False)
    return existing


def _naive(index):
    """Drops any timezone so warehouse dates and query dates compare.

    yfinance history is timezone-aware; a hand-built frame usually is not.
    """
    return index.dt.tz_localize(None) if index.dt.tz is not None else index


def _close_series(historical: pd.DataFrame, symbol: str) -> pd.Series:
    rows = historical[historical["symbol"] == symbol]
    if rows.empty:
        raise NoPriceHistoryError("No history for {}".format(symbol))
    dates = _naive(pd.to_datetime(rows["date"])).dt.normalize()
    return pd.Series(rows["close"].values, index=dates).sort_index()


def _as_of(series: pd.Series, when: datetime, symbol: str) -> Tuple[float, bool]:
    """Latest close at or before `when`, and whether it was carried forward."""
    stamp = pd.Timestamp(when)
    if stamp.tzinfo is not None:
        stamp = stamp.tz_localize(None)
    naive = stamp.normalize()
    eligible = series[series.index <= naive]
    if eligible.empty:
        raise NoPriceHistoryError(
            "No close for {} at or before {}".format(symbol, naive.date())
        )
    return float(eligible.iloc[-1]), eligible.index[-1] < naive


def build_price_table(
    historical: pd.DataFrame,
    tickers: Iterable[str],
    symbol_map: SymbolMap,
    dates: Iterable[datetime],
    base: str,
    extra_currencies: Iterable[str] = (),
) -> Tuple[Dict[datetime, Dict[str, float]], Dict[datetime, List[str]]]:
    """Prices in the base currency for every ticker on every date.

    A missing close carries the last known one forward and records the symbol
    in the stale map. KR and US calendars differ, so on most days one side is
    stale by construction.
    """
    tickers = list(tickers)
    currencies = {symbol_map.currency_of(t) for t in tickers}
    currencies |= set(extra_currencies)
    currencies.add(base)

    close_by_symbol = {t: _close_series(historical, t) for t in tickers}
    fx_by_currency = {}
    for currency in currencies:
        symbol = fx_symbol(currency, base)
        fx_by_currency[currency] = (
            None if symbol is None else _close_series(historical, symbol)
        )

    prices_by_date: Dict[datetime, Dict[str, float]] = {}
    stale_by_date: Dict[datetime, List[str]] = {}

    for when in dates:
        row: Dict[str, float] = {}
        stale: List[str] = []

        # Resolve ticker closes before FX rates: when a date predates all
        # history, this ensures the error names the missing ticker rather
        # than an incidentally-checked FX symbol.
        closes: Dict[str, float] = {}
        for ticker in tickers:
            close, was_stale = _as_of(close_by_symbol[ticker], when, ticker)
            closes[ticker] = close
            if was_stale:
                stale.append(ticker)

        rates: Dict[str, float] = {}
        for currency, series in fx_by_currency.items():
            if series is None:
                rates[currency] = 1.0
            else:
                rate, was_stale = _as_of(series, when, fx_symbol(currency, base))
                rates[currency] = rate
                if was_stale:
                    stale.append(fx_symbol(currency, base))

        for ticker in tickers:
            row[ticker] = closes[ticker] * rates[symbol_map.currency_of(ticker)]

        for currency, rate in rates.items():
            row[cash_ticker(currency)] = rate

        prices_by_date[when] = row
        stale_by_date[when] = sorted(set(stale))

    return prices_by_date, stale_by_date
