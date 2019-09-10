from finance.models import Granularity
from finance.providers import Yahoo


def fetch_stock_values(stock_code, start_date, end_date,
                       granularity=Granularity.day):
    """Fetches stock prices from Yahoo Finance."""
    if start_date > end_date:
        raise ValueError('start_date must be equal to or less than end_date')

    provider = Yahoo()
    rows = provider.asset_values(
        stock_code, start_date, end_date, granularity)

    for row in rows:
        # NOTE: The last column is data source. Not sure if this is an elegant
        # way to handle this.
        yield row + (provider.name,)
