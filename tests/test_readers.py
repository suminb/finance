from finance.readers import load_schema


def test_load_schema():
    schema = load_schema()
    assert schema.fullname == 'io.shortbread.finance.AssetValue'
    assert len(schema.fields) == 11