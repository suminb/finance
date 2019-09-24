from finance.models import Granularity
from finance.providers import Yahoo
from finance.utils import deprecated


@deprecated
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


class AssetValueFetcher:

    def fetch_daily_values(self, *args, **kwargs):
        raise NotImplementedError


class YahooAssetValueFetcher(AssetValueFetcher):

    def fetch_daily_values(self, code, start, end):
        from pandas_datareader import DataReader
        data = DataReader(code, 'yahoo', start, end)

        return data


def Fetcher(data_type, format):
    mappings = {
        # FIXME: Provide another later of abstraction to cope with different
        # data providers
        ('AssetValue', 'dataframe'): YahooAssetValueFetcher,
    }

    def is_supported_type(data_type):
        return data_type in ['AssetValue']

    def is_supported_format(format):
        return format in ['dataframe']

    if not is_supported_type(data_type):
        raise ValueError(f'Unsupported data type: {data_type}')
    if not is_supported_format(format):
        raise ValueError(f'Unsupported format: {format}')
    return mappings[(data_type, format)]()
