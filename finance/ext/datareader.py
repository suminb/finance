"""A module that reads in AssetValue in database and turn them into Pandas DataFrame."""

from datetime import datetime

import pandas as pd

from finance.models import Asset, AssetValue, Granularity


def make_asset_value_dict(asset_value: AssetValue, asset: Asset, base_asset: Asset):
    d = dict(asset_value)
    d["symbol"] = asset.code
    d["base_asset"] = base_asset.code
    return d


def read_asset_value(
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        source: str = "upbit",
        ticker_granularity: Granularity = Granularity.three_min,
):
    asset = Asset.get_by_symbol(symbol)
    base_asset = Asset.get_by_symbol("KRW")
    rows = AssetValue.query \
        .filter(AssetValue.asset == asset) \
        .filter(AssetValue.source == source) \
        .filter(AssetValue.granularity == "15min")
    return pd.DataFrame.from_dict([
        make_asset_value_dict(r, asset, base_asset) for r in rows])

