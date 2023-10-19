"""This is a temporary naming. This module contains code to manage symbols and
historical data."""

from datetime import datetime, timedelta
import os

import pandas as pd
import yfinance as yf


def concat_dataframes(
    df1,
    df2,
    sort_by=["region", "symbol", "updated_at"],
    drop_duplicates_subset=["region", "symbol", "date"],
):
    return (
        pd.concat([df1, df2], ignore_index=True)
        .sort_values(sort_by)
        .drop_duplicates(subset=drop_duplicates_subset, keep="last")
    )


def get_previous_dates(current_datetime=datetime.utcnow(), start=0, up_to=30):
    """Get previous dates up to a point"""
    for d in range(start, up_to + 1):
        yield current_datetime - timedelta(days=d)


def load_tickers(load_datetime=datetime.utcnow()):
    date_format = "%Y%m%d"
    for previous_date in get_previous_dates(load_datetime):
        path = f"tickers-{previous_date.strftime(date_format)}.parquet"
        if os.path.exists(path):
            existing_data = pd.read_parquet(path)
            print(f"Loaded tickers from {previous_date.strftime(date_format)}")
            return existing_data.rename(columns={"fetched_at": "updated_at"})
    return None


def load_historical_data(
    region: str, load_datetime=datetime.utcnow(), base_path="historical"
):
    date_format = "%Y%m%d"
    for previous_date in get_previous_dates(load_datetime):
        path = os.path.join(
            base_path, f"{region}-{previous_date.strftime(date_format)}.parquet"
        )
        if os.path.exists(path):
            existing_data = pd.read_parquet(path)
            print(f"Loaded historical data from {previous_date.strftime(date_format)}")
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


def save_tickers(dataframe: pd.DataFrame, save_datetime=datetime.utcnow()):
    date_format = "%Y%m%d"
    ticker_filename = f"tickers-{save_datetime.strftime(date_format)}.parquet"
    dataframe.to_parquet(ticker_filename)


def save_historical_data(
    dataframe: pd.DataFrame,
    region="US",
    base_path="historical",
    save_datetime=datetime.utcnow(),
):
    date_format = "%Y%m%d"
    path = os.path.join(
        base_path, f"{region}-{save_datetime.strftime(date_format)}.parquet"
    )
    # os.makedirs(os.path.dirname(path), exist_ok=True)
    dataframe.to_parquet(path)
