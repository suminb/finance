"""Responsible for writing DataFrame to a local file.

Potential issues:
  - Writer is tighly coupled with Pandas DataFrame
  - Writer is tighly coupled with Avro
"""
from avro.datafile import DataFileWriter
from avro.io import DatumWriter

from finance.avro import float_to_long

try:
    from backports.datetime_fromisoformat import MonkeyPatch
except ImportError:
    pass
else:
    MonkeyPatch.patch_fromisoformat()


class Writer:

    def write(self, *args, **kwargs):
        raise NotImplementedError


class DataFrameAvroWriter(Writer):

    def write(self, dataframe, provider, fetched_at, schema, filename):
        with DataFileWriter(open(filename, 'wb'), DatumWriter(), schema,
                            codec='deflate') as writer:
            for index, row in dataframe.iterrows():
                writer.append({
                    'asset_id': 0,
                    'evaluated_at': index.isoformat(),
                    'fetched_at': fetched_at.isoformat(),
                    'provider': provider,
                    'granularity': '1day',
                    'open': float_to_long(row['Open']),
                    'close': float_to_long(row['Close']),
                    'high': float_to_long(row['High']),
                    'low': float_to_long(row['Low']),
                    'adj_close': float_to_long(row['Adj Close']),
                    'volume': int(row['Volume']),
                })
