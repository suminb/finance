from datetime import datetime, timedelta
import os

import pandas
import pytest

from finance.readers import load_schema, read_asset_values, Reader


BASE_PATH = os.path.abspath(os.path.dirname(__file__))
PROJECT_PATH = os.path.abspath(os.path.join(BASE_PATH, ".."))


def test_load_schema():
    schema = load_schema()
    assert schema.fullname == "io.shortbread.finance.AssetValue"
    assert len(schema.fields) == 11


# FIXME: data = j["context"]["dispatcher"]["stores"] appears to be a base64 encoded string
@pytest.mark.skip
@pytest.mark.parametrize("force_fetch", [False, True])
def test_read_asset_values(force_fetch):
    end = datetime.now()
    start = end - timedelta(days=30)
    asset_values = read_asset_values("SPY", "yahoo", start, end, force_fetch)

    assert isinstance(asset_values, pandas.core.frame.DataFrame)
    assert len(asset_values.columns) == 11


def test_read_records():
    import types

    filename = os.path.join(BASE_PATH, "samples", "miraeasset_records_euckr.csv")
    reader = Reader("Record", "csv", "plain")

    gen = reader.read(filename)
    assert isinstance(gen, types.GeneratorType)

    records = list(gen)
    assert len(records) == 6


def test_read_records_as_dataframe():
    filename = os.path.join(BASE_PATH, "samples", "miraeasset_records_euckr.csv")
    reader = Reader("Record", "csv", "dataframe")

    data = reader.read(filename)
    assert isinstance(data, pandas.core.frame.DataFrame)
    assert data.shape == (6, 12)
