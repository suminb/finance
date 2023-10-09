"""This is a temporary naming. This module contains code to manage symbols and historical data."""

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


def load_tickers():
    today = datetime.utcnow()
    date_format = "%Y%m%d"
    data_filename = f"tickers-{today.strftime(date_format)}.parquet"

    if os.path.exists(data_filename):
        existing_data = pd.read_parquet(data_filename)
    else:
        existing_data = None
        for d in range(1, 31):
            previous_date = today - timedelta(days=d)
            data_filename = f"tickers-{previous_date.strftime(date_format)}.parquet"
            if os.path.exists(data_filename):
                existing_data = pd.read_parquet(data_filename)
                print(f"Loaded data from {previous_date.strftime(date_format)}")
                break
    return existing_data.rename(columns={"fetched_at": "updated_at"})


def fetch_profile_and_historical_data(symbol: str, region="US", period="5y"):
    ticker = yf.Ticker(symbol)
    updated_at = datetime.utcnow()
    profile = preprocess_profile(ticker.info, symbol, region, updated_at)
    history = preprocess_historical_data(
        ticker.history(period=period), region, period, updated_at
    )
    return profile, history


def preprocess_profile(profile: dict, symbol: str, region: str, updated_at: datetime):
    profile["region"] = region
    profile["symbol"] = symbol
    profile["updated_at"] = updated_at
    profile["quote_type"] = profile.pop("quoteType")
    profile["name"] = profile.pop("longName")

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


def fetch_historical_data(symbol: str, region="US", period="5y"):
    ticker = yf.Ticker(symbol)
    history = ticker.history(period=period)

    return preprocess_historical_data(history, symbol, region)


def load_historical_data(symbol: str, region="US", period="5y", base_path="historical"):
    """Fetch and locally store historical data"""
    fetched = fetch_historical_data(symbol, region, period)
    path = os.path.join(base_path, region, f"{symbol}.parquet")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fetched.to_parquet(path)
    return fetched


def save_historical_data(dataframe: pd.DataFrame, region="US", base_path="historical"):
    path = os.path.join(base_path, f"{region}.parquet")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    dataframe.to_parquet(path)
