"""A collection of data import functions."""
from datetime import datetime

from typedecorator import typed

from finance.models import Asset, AssetValue, get_asset_by_stock_code, \
    Granularity
from finance.providers.provider import AssetValueProvider


@typed
def import_stock_values(provider: AssetValueProvider, code: str,
                        from_date: datetime, to_date: datetime):
    asset = get_asset_by_stock_code(code)
    data = provider.fetch_data(code, from_date, to_date)
    for date, open_, high, low, close_, volume, adj_close in data:
        AssetValue.create(
            evaluated_at=date, granularity=Granularity.day, asset=asset,
            open=open_, high=high, low=low, close=close_, volume=volume)
