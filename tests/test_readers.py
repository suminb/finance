from datetime import datetime

from finance.readers import load_schema, read_asset_values


def test_load_schema():
    schema = load_schema()
    assert schema.fullname == 'io.shortbread.finance.AssetValue'
    assert len(schema.fields) == 11


def test_read_asset_values():
    import pandas

    end = datetime.now()
    start = datetime(end.year - 1, end.month, end.day)
    asset_values = read_asset_values('SPY', 'yahoo', start, end)
    assert isinstance(asset_values, pandas.core.frame.DataFrame)
    assert len(asset_values.columns) == 11
