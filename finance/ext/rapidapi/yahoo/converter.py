from finance.models import AssetValue, Financial, FinancialGranularity, Granularity
from finance.ext.rapidapi.yahoo.models import Financials


def convert_historical_data_prices(asset_id, base_asset_id, prices):
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


def convert_financials(asset_id, financials: Financials):
    keys = ["revenue", "earnings"]
    for earning in financials.quarterly_earnings:
        quarter, year = earning["date"].split("Q")
        for key in keys:
            yield Financial.create(
                asset_id=asset_id,
                key=key,
                granularity=FinancialGranularity.quarterly,
                year=int(year),
                quarter=int(quarter),
                value=earning[key],
                ignore_if_exists=True,
            )

    for earning in financials.yearly_earnings:
        for key in keys:
            yield Financial.create(
                asset_id=asset_id,
                key=key,
                granularity=FinancialGranularity.annual,
                year=int(earning["date"]),
                quarter=0,
                value=earning[key],
                ignore_if_exists=True,
            )
