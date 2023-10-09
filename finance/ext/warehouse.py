"""This is a temporary naming. This module contains code to manage symbols and historical data."""

from datetime import datetime
import os

import pandas as pd
import yfinance as yf


def concat_dataframes(df1, df2):
    return (
        pd.concat([df1, df2], ignore_index=True)
        .sort_values(["region", "symbol", "updated_at"])
        .drop_duplicates(subset=["region", "symbol", "date"], keep="last")
    )


def fetch_historical_data(symbol: str, region="US", period="5y"):
    ticker = yf.Ticker(symbol)
    history = ticker.history(period=period)

    # convert the index to a regular column
    history.reset_index(inplace=True)

    # history.index.names = ["date"]
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
    history["updated_at"] = datetime.utcnow()
    return history


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
