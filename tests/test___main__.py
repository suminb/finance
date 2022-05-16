import os
import random

import pytest
from click.testing import CliRunner

from finance.__main__ import (
    create_all,
    drop_all,
    fetch_stock_values,
    import_fund,
    import_sp500_records,
    import_stock_records,
    import_stock_values,
    insert_stock_assets,
    insert_test_data,
)
from finance.exceptions import AssetNotFoundException
from finance.models import StockAsset, deposit
from finance.utils import load_stock_codes


@pytest.fixture(autouse=True)
def monkeypatch_db_url(monkeypatch):
    monkeypatch.setitem(os.environ, "SBF_DB_URL", os.environ["SBF_TEST_DB_URL"])


def test_drop_all():
    runner = CliRunner()
    result = runner.invoke(drop_all)
    assert result.exit_code == 0


def test_create_all():
    runner = CliRunner()
    result = runner.invoke(create_all)
    assert result.exit_code == 0


@pytest.mark.skip
def test_insert_test_data_all():
    runner = CliRunner()
    result = runner.invoke(insert_test_data)
    assert result.exit_code == 0


@pytest.mark.skip
def test_import_sp500_records():
    runner = CliRunner()
    result = runner.invoke(import_sp500_records)
    assert result.exit_code == 0


@pytest.mark.skip(reason="It appears Kofia API has been changed.")
def test_import_fund(asset_krw, asset_sp500):
    runner = CliRunner()
    result = runner.invoke(import_fund, ["KR5223941018", "2016-01-01", "2016-01-31"])
    assert result.exit_code == 0


def test_import_non_existing_fund():
    runner = CliRunner()
    result = runner.invoke(import_fund, ["???", "2016-01-01", "2016-01-31"])
    assert isinstance(result.exception, AssetNotFoundException)


@pytest.mark.skip(reason="Yahoo Finance provider is scheduled to be deprecated.")
def test_fetch_stock_values():
    runner = CliRunner()
    result = runner.invoke(
        fetch_stock_values, ["NVDA", "-s", "2017-01-01", "-e", "2017-01-15"]
    )
    assert result.exit_code == 0


# NOTE: This test case may intermittently fail as some of the stock codes
# is not available for download in Google Finance
def test_import_stock_values():
    with open("stock_codes.csv", "r") as fin:
        codes = list(load_stock_codes(fin))

    code, name = random.choice(codes)
    StockAsset.create(code=code)

    runner = CliRunner()
    result = runner.invoke(
        import_stock_values,
        [code],
        input="2017-08-28, 31100.0, 31150.0, 30400.0, 31000.0, 856210, test",
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    asset = StockAsset.get_by_symbol(code)
    asset_value = asset.asset_values[0]

    assert asset_value.open == 31100
    assert asset_value.high == 31150
    assert asset_value.low == 30400
    assert asset_value.close == 31000
    assert asset_value.volume == 856210


def test_import_stock_records(session, asset_krw, account_stock, account_checking):
    for _ in insert_stock_assets():
        pass

    runner = CliRunner()
    result = runner.invoke(
        import_stock_records,
        ["tests/samples/shinhan_stock_records.csv"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
