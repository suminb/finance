"""This is a temporary naming. This module contains code to manage symbols and
historical data."""

from datetime import datetime, timedelta
from itertools import combinations
from math import factorial
import os
import random
import time

from logbook import Logger
import pandas as pd
import polars as pl
from rich.progress import Progress
import yfinance as yf

from finance.ext.exceptions import TickerNotFoundException

from typing import List


log = Logger(__file__)


def concat_dataframes(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    sort_by=["region", "symbol", "updated_at"],
    drop_duplicates_subset=["region", "symbol", "date"],
) -> pd.DataFrame:
    return (
        pd.concat([df1, df2], ignore_index=True)
        .sort_values(sort_by)
        .drop_duplicates(subset=drop_duplicates_subset, keep="last")
    )


def get_previous_dates(current_datetime=datetime.utcnow(), start=0, up_to=30):
    """Get previous dates up to a point"""
    for d in range(start, up_to + 1):
        yield current_datetime - timedelta(days=d)


def fetch_profile_and_historical_data(symbol: str, region="US", period="5y"):
    ticker = yf.Ticker(symbol)
    if "quoteType" not in ticker.info:
        raise TickerNotFoundException
    # TODO: What happens when the server returns 5xx (or 4xx other than 404)?
    updated_at = datetime.utcnow()
    profile = preprocess_profile(ticker.info, symbol, region, updated_at)
    history = preprocess_historical_data(
        ticker.history(period=period), symbol, region, updated_at
    )
    return profile, history


def preprocess_profile(profile: dict, symbol: str, region: str, updated_at: datetime):
    profile["region"] = region
    profile["symbol"] = symbol
    profile["updated_at"] = updated_at
    profile["quote_type"] = profile.pop("quoteType")
    if "longName" in profile:
        profile["name"] = profile.pop("longName")
    elif "shortName" in profile:
        profile["name"] = profile.pop("shortName")
    else:
        profile["name"] = None

    profile.setdefault("sector", None)
    profile.setdefault("industry", None)
    profile.setdefault("longBusinessSummary", None)
    profile["long_business_summary"] = profile.pop("longBusinessSummary")

    if "close" not in profile:
        profile["close"] = profile[
            "previousClose"
        ]  # Not sure if these two are the same
    if profile["quote_type"] == "ETF":
        profile["market_cap"] = profile.pop("totalAssets")
    else:
        profile["market_cap"] = profile.pop("marketCap")
    return profile


def preprocess_historical_data(
    history: pd.DataFrame, symbol: str, region: str, updated_at: datetime
):
    # convert the index to a regular column
    history.reset_index(inplace=True)

    history = history.rename(
        columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
            "Dividends": "dividends",
            "Stock Splits": "stock_splits",
            "Capital Gains": "capital_gains",
        }
    )
    history["region"] = region
    history["symbol"] = symbol
    history["updated_at"] = updated_at
    return history


def fetch_historical_data(
    symbol: str, region="US", period="5y", updated_at=datetime.utcnow()
):
    ticker = yf.Ticker(symbol)
    history = ticker.history(period=period)

    return preprocess_historical_data(history, symbol, region, updated_at)


def refresh_tickers_and_historical_data(
    region: str,
    tickers_source: pd.DataFrame,
    staging_path: str,
    tickers_target_path: str,
    historical_target_path: str,
    symbols: List[str],
    delay_factor: float = 2.0,
):
    ticker_keys = [
        "region",
        "symbol",
        "exchange",
        "quote_type",
        "currency",
        "name",
        "sector",
        "industry",
        "close",
        "volume",
        "market_cap",
        "updated_at",
        "long_business_summary",
        "status",
    ]

    # Filter tickers that were updated older than a day ago
    tickers = tickers_source.copy()

    # profile_base_path = os.path.join(staging_path, "profiles")
    historical_base_path = os.path.join(staging_path, "historical")
    os.makedirs(historical_base_path, exist_ok=True)

    with Progress() as progress:
        task = progress.add_task("[red]Fetching", total=len(symbols))
        for symbol in symbols:
            progress.update(task, description=f"Fetching[{symbol}]", advance=1)
            dt = datetime.utcnow().strftime("%Y%m%d")

            skip_marker_path = os.path.join(
                historical_base_path, f".{region}-{symbol}-{dt}.skip"
            )
            if os.path.exists(skip_marker_path):
                log.info(f"Skipping {symbol}...")
                continue

            try:
                profile, history_new = fetch_profile_and_historical_data(
                    symbol, region, period="max"
                )
            except TickerNotFoundException:
                log.warn(f"{symbol} not found")
                row_indexer = tickers.symbol == symbol
                tickers.loc[row_indexer, "updated_at"] = datetime.utcnow()
                # TODO: Define enum instead of using string literals
                tickers.loc[row_indexer, "status"] = "delisted"
                tickers.to_parquet(tickers_target_path)
            except Exception as e:
                log.warn(f"{symbol}: {e}")
                with open(skip_marker_path, "w") as fout:
                    fout.write(str(e))
            else:
                profile = pd.DataFrame(
                    [{k: profile[k] for k in ticker_keys if k in profile}]
                )
                history_new.to_parquet(
                    os.path.join(
                        historical_base_path, f"{region}-{symbol}-{dt}.parquet"
                    )
                )

                # By placing the new dataframe prior to the existing one,
                # we can easily re-order columns
                tickers = concat_dataframes(
                    profile, tickers, drop_duplicates_subset=["region", "symbol"]
                )

                # This is wasteful, but an acceptable practice not to lose data
                tickers.to_parquet(tickers_target_path)

                time.sleep(random.random() * delay_factor)

        historical = pd.read_parquet(historical_base_path)
        historical.drop_duplicates(
            subset=["date", "region", "symbol"], keep="last"
        ).to_parquet(historical_target_path)


def calc_pairwise_correlations(
    historical_by_symbols: pd.DataFrame, row: pd.Series
) -> List[float]:
    combination_indices = row[0]
    return [
        historical_by_symbols[i].corr(historical_by_symbols[j])
        for i, j in combinations(combination_indices, 2)
    ]


def calc_overall_correlation(row: pd.Series) -> float:
    pairwise_correlations = row[0]
    n = len(pairwise_correlations)
    return sum(c**2 for c in pairwise_correlations) * (1 / n)


def make_combination_indices(
    indices: List[int], static_indices: List[int], r: int, partitions: int
):
    n, r = len(indices), r - len(static_indices)
    assert r >= 1, "r must be greater than or equal to 1"
    assert r <= n, "n must be less than or equal to r"
    ncr = int(factorial(n) / (factorial(r) * factorial(n - r)))
    count_per_partition = ncr // partitions
    log.debug(f"n={n}, r={r}, ncr={ncr}, count_per_partitions={count_per_partition}")
    comb_g = combinations([i for i in indices if i not in set(static_indices)], r)

    def generate_combination_indices():
        for _ in range(count_per_partition):
            try:
                indices = static_indices + list(next(comb_g))
            except StopIteration:
                break
            yield indices

    for p in range(partitions):
        log.info(f"Generating combination indices: partition {p}/{partitions}")
        yield list(generate_combination_indices())


def filter_tickers(
    tickers: pl.DataFrame, region: str, market_cap_trheshold: float = 5e9
) -> pd.DataFrame:
    # US ETFs only
    tickers = tickers.filter(
        (pl.col("quote_type") == "ETF") & (pl.col("region") == region)
    )

    # Filter by market cap
    tickers = tickers.filter(tickers["market_cap"] >= market_cap_trheshold)

    # Exclude leveraged ETFs
    tickers = tickers.filter(
        ~tickers["name"].str.contains("2X") & ~tickers["name"].str.contains("3X")
    )
    return tickers


# NOTE: Why this can't be concurrent?
def map_sector_indices(
    tickers: pl.DataFrame, sector_index_map: dict, combination_indices: List[int]
):
    sector_values = (tickers[i]["sector"][0] for i in combination_indices)
    return [sector_index_map[s] for s in sector_values]
    # return [sectors.index(s) for s in sector_values]
