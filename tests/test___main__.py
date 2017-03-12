from click.testing import CliRunner

from finance.__main__ import *  # noqa
from finance.exceptions import AssetNotFoundException


def test_drop_all():
    runner = CliRunner()
    result = runner.invoke(drop_all)
    assert result.exit_code == 0


def test_create_all():
    runner = CliRunner()
    result = runner.invoke(create_all)
    assert result.exit_code == 0


def test_insert_test_data_all():
    runner = CliRunner()
    result = runner.invoke(insert_test_data)
    assert result.exit_code == 0


def test_import_8percent(account_checking, account_8p, asset_krw):
    runner = CliRunner()
    result = runner.invoke(import_8percent, ['tests/data/8percent-829.html'],
                           catch_exceptions=False)
    assert result.exit_code == 0


def _test_import_sp500():
    runner = CliRunner()
    result = runner.invoke(import_sp500)
    assert result.exit_code == 0


def test_import_fund(asset_sp500):
    runner = CliRunner()
    result = runner.invoke(import_fund,
                           ['KR5223941018', '2016-01-01', '2016-01-31'])
    assert result.exit_code == 0


def test_import_non_existing_fund():
    runner = CliRunner()
    result = runner.invoke(import_fund, ['???', '2016-01-01', '2016-01-31'])
    assert isinstance(result.exception, AssetNotFoundException)


def test_import_stock_values():
    runner = CliRunner()
    result = runner.invoke(import_stock_values,
                           ['005380.KS', '2000-01-01', '2016-07-03'],
                           catch_exceptions=False)
    assert result.exit_code == 0


def test_import_stock_records(asset_krw, account_stock, account_checking):
    from finance.__main__ import insert_stock_assets
    for _ in insert_stock_assets():
        pass

    runner = CliRunner()
    result = runner.invoke(import_stock_records, ['tests/data/stocks.csv'],
                           catch_exceptions=False)
    assert result.exit_code == 0


def teardown_module(module):
    runner = CliRunner()
    runner.invoke(drop_all)
