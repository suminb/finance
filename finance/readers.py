from datetime import datetime
import os

import avro.schema
from avro.datafile import DataFileReader
from avro.io import DatumReader
from pandas import DataFrame

from finance.avro import long_to_float
from finance.fetchers import Fetcher
from finance.providers import is_valid_provider, Miraeasset
from finance.writers import Writer


def get_local_copy_path(code, provider):
    # TODO: Perhaps we should consider checking against start/end datetime
    return f'{provider}_{code}.avro'


def load_schema():
    schema_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'asset_values.avsc')
    schema = avro.schema.Parse(open(schema_path, 'rb').read())

    return schema


def read_asset_values(code, provider, start, end, force_fetch=False,
                      source_format='avro', target_format='dataframe'):
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
        fetcher = Fetcher('AssetValue', 'dataframe')
        data = fetcher.fetch_daily_values(code, start, end)
        fetched_at = datetime.now()

        writer = Writer('AssetValue', target_format, source_format)
        writer.write(data, 'yahoo', fetched_at, schema, local_copy_path)

    reader = Reader('AssetValue', source_format, target_format)
    return reader.read(local_copy_path)


class AbstractReader:

    def read(self, *args, **kwargs):
        raise NotImplementedError


class AssetValueAvroDataFrameReader(AbstractReader):

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


class RecordCSVPlainReader(AbstractReader):

    def __init__(self):
        # TODO: Allow other providers
        self.provider = Miraeasset()

    def read(self, filename):
        for row in self.provider.read_records(filename):
            yield row


class RecordCSVDataFrameReader(RecordCSVPlainReader):

    def read(self, filename):
        records = super(RecordCSVDataFrameReader, self).read(filename)
        from finance.providers.miraeasset import Record
        # FIXME: Can we do this without x.values()?
        return DataFrame([x.values() for x in records], columns=Record.attributes)


def Reader(data_type, source_format, target_format):
    mappings = {
        ('AssetValue', 'avro', 'dataframe'): AssetValueAvroDataFrameReader,
        ('Record', 'csv', 'plain'): RecordCSVPlainReader,
        ('Record', 'csv', 'dataframe'): RecordCSVDataFrameReader,
    }

    def is_supported_type(data_type):
        return data_type in ['AssetValue', 'Record']

    def is_supported_source_format(format):
        return format in ['avro', 'csv']

    def is_supported_target_format(format):
        return format in ['plain', 'dataframe']

    if not is_supported_type(data_type):
        raise ValueError(f'Unsupported data type: {data_type}')
    if not is_supported_source_format(source_format):
        raise ValueError(f'Unsupported source format: {source_format}')
    if not is_supported_target_format(target_format):
        raise ValueError(f'Unsupported target format: {target_format}')
    return mappings[(data_type, source_format, target_format)]()
