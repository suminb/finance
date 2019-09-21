from datetime import datetime
import os

import avro.schema
from avro.datafile import DataFileReader, DataFileWriter
from avro.io import DatumReader, DatumWriter
from pandas import DataFrame


# TODO: Move this elsewhere
def is_valid_provider(provider):
    return provider in ['yahoo']


def get_local_copy_path(code, provider):
    # TODO: Perhaps we should consider checking against start/end datetime
    return f'{provider}_{code}.avro'


def process_local_copy(reader):
    for row in reader:
        row['evaluated_at'] = datetime.fromisoformat(row['evaluated_at'])
        for k in ['open', 'close', 'high', 'low', 'adj_close']:
            row[k] = long_to_float(row[k])
        yield row


def read_asset_values(code, provider, start, end, force_fetch=False):
    """Reads asset values for a particular time period.

    :param start: Start datetime (lowerbound of the time period)
    :param end: End datetime (upperbound of the time period)
    """
    if not is_valid_provider(provider):
        raise ValueError(f'Invalid provider: {provider}')

    # check if locally available
    local_copy_path = get_local_copy_path(code, provider)

    schema_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'asset_values.avsc')
    schema = avro.schema.Parse(open(schema_path, 'rb').read())

    if force_fetch or not os.path.exists(local_copy_path):
        # if not, fetch from the provider
        from pandas_datareader import DataReader
        data = DataReader(code, provider, start, end)

        with DataFileWriter(open(local_copy_path, 'wb'), DatumWriter(), schema, codec='deflate') as writer:
            for index, row in data.iterrows():
                writer.append({
                    'asset_id': 0,
                    'evaluated_at': index.isoformat(),
                    'provider': provider,
                    'granularity': '1day',
                    'open': float_to_long(row['Open']),
                    'close': float_to_long(row['Close']),
                    'high': float_to_long(row['High']),
                    'low': float_to_long(row['Low']),
                    'adj_close': float_to_long(row['Adj Close']),
                    'volume': int(row['Volume']),
                })
         
    with DataFileReader(open(local_copy_path, 'rb'), DatumReader()) as reader:
        return DataFrame(process_local_copy(reader))


def float_to_long(value):
    return int(value * 1000000)


def long_to_float(value):
    return value / 1000000.0