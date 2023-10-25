"""This is a temporary naming. This module contains code to manage symbols and
historical data."""

from datetime import datetime, timedelta
import os
import random
import time

from logbook import Logger
import pandas as pd
from rich.progress import Progress
import yfinance as yf

from typing import Optional


log = Logger(__file__)


def concat_dataframes(
    df1,
    df2,
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


def load_tickers(path: str) -> Optional[pd.DataFrame]:
    """Load tickers from a file."""
    # TODO: Currently Parquet only. Add support for other file types like CSV, JSON, etc.
    if os.path.exists(path):
        existing_data = pd.read_parquet(path)
        log.info(f"Loaded tickers from {path}")
        return existing_data.rename(columns={"fetched_at": "updated_at"})
    return None


def load_historical_data(path: str) -> Optional[pd.DataFrame]:
    if os.path.exists(path):
        existing_data = pd.read_parquet(path)
        log.info(f"Loaded historical data from {path}")
        return existing_data
    return None


def fetch_profile_and_historical_data(symbol: str, region="US", period="5y"):
    ticker = yf.Ticker(symbol)
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
    historical_source: pd.DataFrame,
    tickers_target_path: str,
    historical_target_path: str,
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
    filtered = tickers_source.copy()
    now = datetime.utcnow()
    filtered["time_elapsed"] = filtered["updated_at"].apply(lambda x: (now - x).days)
    filtered = filtered[filtered["time_elapsed"] >= 1]

    # filtered = tickers[(tickers["quote_type"] == "EQUITY") & (tickers["region"] == region)]
    # filtered = filtered.sort_values("updated_at", ascending=True)

    symbols = filtered["symbol"].tolist()

    history_keys = [
        "region",
        "symbol",
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "dividends",
        "stock_splits",
        "capital_gains",
        "updated_at",
    ]

    history = historical_source.copy()
    with Progress() as progress:
        task = progress.add_task("[red]Fetching", total=len(symbols))
        for symbol in symbols:
            progress.update(task, description=f"Fetching[{symbol}]", advance=1)

            try:
                profile, history_new = fetch_profile_and_historical_data(symbol, region)
            except Exception as e:
                log.warn(f"{symbol}: {e}")
                profile = pd.DataFrame(
                    [
                        {
                            "region": region,
                            "symbol": symbol,
                            "status": "error",
                            "updated_at": datetime.utcnow(),
                        }
                    ]
                )
                history_new = None
            else:
                profile = pd.DataFrame(
                    [{k: profile[k] for k in ticker_keys if k in profile}]
                )

            # By placing the new dataframe prior to the existing one, we can easily re-order columns
            tickers = concat_dataframes(
                profile, tickers, drop_duplicates_subset=["region", "symbol"]
            )
            history = concat_dataframes(history_new, history)

            # This is wasteful, but an acceptable practice not to lose data
            tickers.to_parquet(tickers_target_path)

            history.to_parquet(historical_target_path)
            time.sleep(random.random() * 3)
