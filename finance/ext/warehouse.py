"""This is a temporary naming. This module contains code to manage symbols and
historical data."""

from datetime import datetime, timedelta
from functools import reduce
from itertools import combinations
from math import ceil, floor, factorial
import os
import random
import time

from logbook import Logger
import pandas as pd
from rich.progress import Progress
import yfinance as yf

from typing import List, Optional, Tuple


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
    staging_path: str,
    tickers_target_path: str,
    historical_target_path: str,
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

    # profile_base_path = os.path.join(staging_path, "profiles")
    historical_base_path = os.path.join(staging_path, "historical")
    os.makedirs(historical_base_path, exist_ok=True)

    with Progress() as progress:
        task = progress.add_task("[red]Fetching", total=len(symbols))
        for symbol in symbols:
            progress.update(task, description=f"Fetching[{symbol}]", advance=1)
            dt = datetime.utcnow().strftime("%Y%m%d")

            skip_marker_path = os.path.join(
                historical_base_path, f"{region}-{symbol}-{dt}.skip"
            )
            if os.path.exists(skip_marker_path):
                log.info(f"Skipping {symbol}...")
                continue

            try:
                profile, history_new = fetch_profile_and_historical_data(
                    symbol, region, period="10y"
                )
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

                # By placing the new dataframe prior to the existing one, we can easily re-order columns
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


def make_correlation_matrix(
    historical: pd.DataFrame, symbols: List[str]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    # This works but very slow (450ms vs < 0.2ms)
    # symbols = historical.groupby("symbol")["symbol"].apply(lambda x: x[0]).values

    historical_by_symbols = rearrange_historical_data_by_symbols(historical, symbols)

    import sklearn.preprocessing as preprocessing

    min_max_scaler = preprocessing.MinMaxScaler()
    scaled_values = pd.DataFrame(
        min_max_scaler.fit_transform(historical_by_symbols),
        columns=historical_by_symbols.columns,
        index=historical_by_symbols.index,
    )
    return scaled_values.corr(), scaled_values


def calc_correlation(corr_matrix: pd.DataFrame, indices: List[int]):
    """Multivariate correlation analysis for a given correlation matrix."""
    n = len(indices)
    xs = [corr_matrix.values[i][j] ** 2 for i, j in combinations(indices, 2)]
    m = reduce(lambda x, y: x * y, xs)
    return m ** (1 / n)


def calc_pairwise_correlations(corr_matrix, indices: List[int]):
    return [corr_matrix.values[i][j] ** 2 for i, j in combinations(indices, 2)]


def calc_overall_correlation(corr_matrix, indices: List[int]):
    n = len(indices)
    pairwise_correlations = calc_pairwise_correlations(corr_matrix, indices)
    m = reduce(lambda x, y: x * y, pairwise_correlations)
    return m ** (1 / n), pairwise_correlations


def rearrange_historical_data_by_symbols(
    historical: pd.DataFrame, symbols: List[str]
) -> pd.DataFrame:
    historical = historical.set_index("date")
    historical_by_symbols = pd.DataFrame(columns=[s for s in symbols])
    with Progress() as progress:
        task = progress.add_task(
            "[red]Rearranging historical data by symbol...", total=len(symbols)
        )
        for symbol in symbols:
            try:
                historical_by_symbols[symbol] = historical[
                    historical["symbol"] == symbol
                ]["close"]
            except KeyError as e:
                log.warn(f"KeyError for {symbol}: {e}")
            progress.advance(task)

    return historical_by_symbols.fillna(0)


def make_combination_indices(
    indices: List[str], r: int, static_indices: List[int] = []
) -> List[List[int]]:
    n, r = len(indices), r - len(static_indices)
    assert r >= 1, "r must be greater than or equal to 1"
    assert r <= n, "n must be less than or equal to r"
    ncr = int(factorial(n) / (factorial(r) * factorial(n - r)))
    log.debug(f"n={n}, r={r}, ncr={ncr}")
    comb_g = combinations([i for i in indices if i not in set(static_indices)], r)

    with Progress() as progress:
        task = progress.add_task("[red]Making combinations...", total=int(ncr))

        def generate_combination_indices():
            for _ in range(ncr):
                try:
                    yield static_indices + list(next(comb_g))
                except StopIteration:
                    break
                progress.advance(task)

        return list(generate_combination_indices())


class Portfolio:
    # TODO: Get rid of dependencies on DataFrame
    def __init__(
        self,
        inventory: dict,
        current_prices: dict,
        target_weights: dict,
    ):
        self.inventory = inventory  # ticker: quantity
        self.current_prices = current_prices  # ticker: price
        self.target_weights = self.normalize_weights(target_weights)  # ticker: weight

    @property
    def asset_values(self):
        return {t: self.current_prices[t] * q for t, q in self.inventory.items()}

    @property
    def net_asset_value(self):
        return sum(self.asset_values.values())

    @property
    def current_weights(self):
        """Calculate the weights of the current holdings based on the current price."""
        nav = self.net_asset_value
        return {t: v / nav for t, v in self.asset_values.items()}

    def normalize_weights(self, weights: dict):
        net_weight = sum(weights.values())
        return {t: v / net_weight for t, v in weights.items()}

    def calc_diff(self):
        """Calculate the difference between the target weights and the current ones."""
        cw = self.current_weights
        tw = self.target_weights
        all_keys = set(list(cw.keys()) + list(tw.keys()))

        def diff(t, cw, tw):
            cw.setdefault(t, 0)
            tw.setdefault(t, 0)
            return cw[t] - tw[t]

        return {t: diff(t, cw, tw) for t in all_keys}

    # TODO: Incorporate tax and fees
    def make_rebalancing_plan(self):
        """
        Negative diff means we're short of that asset, so we need to buy more; whereas positive diff means we need to sell some.
        Positive values in rebalance plans means the quantity of the asset to be purchased.
        """
        nav = self.net_asset_value
        diff = self.calc_diff()

        def plan(t, diff):
            if diff[t] > 0:
                round = ceil
            else:
                round = floor
            return round((nav * -diff[t]) / self.current_prices[t])

        return {t: plan(t, diff) for t in diff if t != "_USD"}

    # TODO: Tax on dividends?
    # TODO: Transaction fees?
    def apply_plan(
        self, plan: dict, start_dt: datetime, end_dt: datetime, dividend_records: dict
    ):
        def apply(t, q):
            self.inventory.setdefault(t, 0)
            self.inventory["_USD"] -= self.current_prices[t] * q
            return self.inventory[t] + q

        self.inventory["_USD"] += self.calc_dividends_sum(
            start_dt, end_dt, dividend_records
        )
        self.inventory = {t: apply(t, q) for t, q in plan.items()} | {
            "_USD": self.inventory["_USD"]
        }
        return self.inventory

    def calc_dividends_sum(
        self, start_dt: datetime, end_dt: datetime, dividend_records: dict
    ) -> float:
        div_sum = 0.0
        for t, q in self.inventory.items():
            if t in dividend_records:
                for div_dt, div_amount in dividend_records[t]:
                    if start_dt <= div_dt <= end_dt:
                        assert q >= 0
                        div_sum += div_amount * q
        return div_sum
