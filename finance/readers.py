from datetime import datetime
import os

import avro.schema
from avro.datafile import DataFileReader
from avro.io import DatumReader
from pandas import DataFrame

from finance.avro import long_to_float
from finance.fetchers import YahooFetcher
from finance.providers import is_valid_provider
from finance.writers import DataFrameAvroWriter


def get_local_copy_path(code, provider):
    # TODO: Perhaps we should consider checking against start/end datetime
    return f'{provider}_{code}.avro'


def load_schema():
    schema_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'asset_values.avsc')
    schema = avro.schema.Parse(open(schema_path, 'rb').read())

    return schema


def read_asset_values(code, provider, start, end, force_fetch=False):
    """Reads asset values for a particular time period.

    :param code:
    :param provider:
    :param start: Start datetime (lowerbound of the time period)
    :param end: End datetime (upperbound of the time period)
    :force_fetch: If true, it fetches data from the remote source even if a
                  local copy exists.
    """
    if not is_valid_provider(provider):
        raise ValueError(f'Invalid provider: {provider}')

    local_copy_path = get_local_copy_path(code, provider)
    schema = load_schema()

    if force_fetch or not os.path.exists(local_copy_path):
        fetcher = YahooFetcher()
        data = fetcher.fetch_daily_values(code, start, end)
        fetched_at = datetime.now()

        writer = DataFrameAvroWriter()
        writer.write(data, 'yahoo', fetched_at, schema, local_copy_path)

    reader = AvroDataFrameReader()
    return reader.read(local_copy_path)


class Reader:

    def read(self, *args, **kwargs):
        raise NotImplementedError


class AvroDataFrameReader(Reader):

    def read(self, filename):
        with DataFileReader(open(filename, 'rb'), DatumReader()) as reader:
            return DataFrame(self.process_local_copy(reader))

    def process_local_copy(self, reader):
        for row in reader:
            row['evaluated_at'] = datetime.fromisoformat(row['evaluated_at'])
            row['fetched_at'] = datetime.fromisoformat(row['fetched_at'])
            for k in ['open', 'close', 'high', 'low', 'adj_close']:
                row[k] = long_to_float(row[k])
            yield row
