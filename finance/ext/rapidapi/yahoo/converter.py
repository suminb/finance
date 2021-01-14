from finance.models import AssetValue, Granularity


def convert_prices_to_asset_values(asset_id, base_asset_id, prices):
    """HistoricalData.prices -> list(AssetValue)"""
    for price in prices:
        yield AssetValue.create(
            asset_id=asset_id,
            base_asset_id=base_asset_id,
            evaluated_at=price["date"],
            source="yahoo",
            granularity=Granularity.day,
            open=price["open"],
            high=price["high"],
            low=price["low"],
            close=price["close"],
            volume=price["volume"],
            ignore_if_exists=True,
        )
