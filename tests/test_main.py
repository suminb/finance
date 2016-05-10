from click.testing import CliRunner

from finance.__main__ import (
    create_all, drop_all, import_8percent, import_sp500, insert_test_data)


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


def test_import_8percent():
    runner = CliRunner()
    result = runner.invoke(import_8percent, ['tests/data/8percent-829.html'])
    assert result.exit_code == 0


def test_import_sp500():
    runner = CliRunner()
    result = runner.invoke(import_sp500)
    assert result.exit_code == 0


def teardown_module(module):
    runner = CliRunner()
    runner.invoke(drop_all)
