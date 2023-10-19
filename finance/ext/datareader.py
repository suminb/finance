"""A module that reads in AssetValue in database and turn them into Pandas DataFrame."""

from datetime import datetime, timedelta

import pandas as pd

from finance.models import Asset, AssetValue, Granularity


def make_asset_value_tuple(
    asset_value: AssetValue, asset: Asset, base_asset: Asset, columns: list
):
    row = [getattr(asset_value, col) for col in columns[:-2]]
    row.append(asset.code)
    row.append(base_asset.code)
    # d = dict(asset_value)
    # d["symbol"] = asset.code
    # d["base_asset"] = base_asset.code
    return row


def read_asset_values(
    symbol: str,
    from_date: datetime = datetime.now() - timedelta(days=365),
    to_date: datetime = datetime.now(),
    source: str = "upbit",
    ticker_granularity: str = Granularity.fifteen_min,
) -> pd.DataFrame:
    columns = [
        "id",
        "evaluated_at",
        "granularity",
        "open",
        "close",
        "low",
        "high",
        "volume",
        "symbol",
        "base_asset",
    ]

    asset = Asset.get_by_symbol(symbol)
    base_asset = Asset.get_by_symbol("KRW")
    rows = (
        AssetValue.query.filter(AssetValue.asset == asset)
        .filter(AssetValue.source == source)
        .filter(AssetValue.granularity == ticker_granularity)
        .filter(AssetValue.evaluated_at >= from_date)
        .filter(AssetValue.evaluated_at <= to_date)
        .order_by(AssetValue.evaluated_at)
    )
    return pd.DataFrame.from_records(
        [make_asset_value_tuple(r, asset, base_asset, columns) for r in rows],
        columns=columns,
    )


def attach_indicators(data_frame: pd.DataFrame, base_column="close") -> pd.DataFrame:
    rolling_periods = [7, 15, 50, 120, 240, 360]
    for rp in rolling_periods:
        data_frame[f"ma{rp}"] = data_frame[base_column].rolling(rp).mean()

    stddiv = data_frame[base_column].rolling(20).std()
    data_frame["bb_upper"] = data_frame["ma20"] + stddiv * 2
    data_frame["bb_lower"] = data_frame["ma20"] - stddiv * 2

    return data_frame
