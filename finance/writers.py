"""Responsible for writing DataFrame to a local file.

Potential issues:
  - Writer is tighly coupled with Pandas DataFrame
  - Writer is tighly coupled with Avro
"""
from avro.datafile import DataFileWriter
from avro.io import DatumWriter


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
                    'open': self.float_to_long(row['Open']),
                    'close': self.float_to_long(row['Close']),
                    'high': self.float_to_long(row['High']),
                    'low': self.float_to_long(row['Low']),
                    'adj_close': self.float_to_long(row['Adj Close']),
                    'volume': int(row['Volume']),
                })

    def float_to_long(self, value):
        return int(value * 1000000)

    def long_to_float(self, value):
        return value / 1000000.0
