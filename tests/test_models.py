from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from finance.exceptions import (AssetNotFoundException,
                                AssetValueUnavailableException)
from finance.models import (
    Account, Asset, AssetValue, Granularity, Portfolio, Record, RecordType,
    Transaction, TransactionState, db, balance_adjustment, deposit,
    get_asset_by_fund_code)
from finance.utils import parse_date, parse_datetime


def test_create_model():
    Account.create(institution='Chase', number='1234')

    # IntegrityError is raised due to the unique constraint
    with pytest.raises(IntegrityError):
        Account.create(institution='Chase', number='1234')

    assert not Account.create(institution='Chase', number='1234',
                              ignore_if_exists=True)


def test_stock_asset(stock_asset_ncsoft):
    assert stock_asset_ncsoft.bps
    assert stock_asset_ncsoft.eps


def test_get_asset_by_fund_code(asset_sp500):
    asset = get_asset_by_fund_code('KR5223941018')
    assert asset.name == 'KB Star S&P500'


def test_get_asset_by_fund_code_non_existing(asset_sp500):
    with pytest.raises(AssetNotFoundException):
        get_asset_by_fund_code('non-exisiting')


def test_get_asset_by_symbol(stock_asset_ncsoft):
    asset = Asset.get_by_symbol('036570.KS')
    assert asset.description == 'NCsoft Corporation'


def test_get_asset_by_symbol_non_existing(asset_sp500):
    with pytest.raises(AssetNotFoundException):
        Asset.get_by_symbol('non-exisiting')


def test_get_asset_by_isin(stock_asset_nvda):
    asset = Asset.get_by_isin('US67066G1040')
    assert asset.code == 'NVDA'


def test_get_asset_by_isin_non_existing(stock_asset_nvda):
    with pytest.raises(AssetNotFoundException):
        Asset.get_by_isin('non-exisiting')


def test_balance(account_checking, asset_krw, asset_usd):
    assert account_checking.balance() == {}

    deposit(account_checking, asset_krw, 1000, parse_date('2016-05-01'))
    assert account_checking.balance(parse_date('2016-05-19')) \
        == {asset_krw: 1000}

    deposit(account_checking, asset_krw, -500, parse_date('2016-05-02'))
    assert account_checking.balance(parse_date('2016-05-19')) \
        == {asset_krw: 500}

    deposit(account_checking, asset_usd, 25, parse_date('2016-05-03'))
    assert account_checking.balance(parse_date('2016-05-19')) \
        == {asset_krw: 500, asset_usd: 25}

    balance_adjustment(
        account_checking, asset_usd, 40, parse_date('2016-05-04'))
    assert account_checking.balance(parse_date('2016-05-19')) \
        == {asset_krw: 500, asset_usd: 40}


def test_portfolio(account_hf, asset_hf1, account_checking, asset_krw):
    portfolio = Portfolio()
    portfolio.base_asset = asset_krw
    portfolio.add_accounts(account_hf, account_checking)

    deposit(account_checking, asset_krw, 500000, parse_date('2015-12-04'))

    with Transaction.create() as t:
        deposit(account_checking, asset_krw, -500000, parse_date('2015-12-04'),
                t)
        deposit(account_hf, asset_hf1, 1, parse_date('2015-12-04'), t)

    # The net asset value shall not be available at this point
    with pytest.raises(AssetValueUnavailableException):
        net_worth = portfolio.net_worth(evaluated_at=parse_date('2015-12-04'),
                                        granularity=Granularity.day)

    # Initial asset value
    AssetValue.create(
        evaluated_at=parse_date('2015-12-04'), asset=asset_hf1,
        base_asset=asset_krw, granularity=Granularity.day, close=500000)

    net_worth = portfolio.net_worth(evaluated_at=parse_date('2015-12-04'),
                                    granularity=Granularity.day)
    assert 500000 == net_worth

    # 1st payment
    interest, tax, returned = 3923, 740, 30930
    deposit(account_checking, asset_krw, returned, parse_date('2016-01-08'))

    # Remaining principle value after the 1st payment
    AssetValue.create(
        evaluated_at=parse_date('2016-01-08'), asset=asset_hf1,
        base_asset=asset_krw, granularity=Granularity.day, close=472253)

    net_worth = portfolio.net_worth(evaluated_at=parse_date('2016-01-08'),
                                    granularity=Granularity.day)
    assert 500000 + (interest - tax) == net_worth

    # 2nd payment
    deposit(account_checking, asset_krw, 25016, parse_date('2016-02-05'))
    # Remaining principle value after the 2nd payment
    AssetValue.create(
        evaluated_at=parse_date('2016-02-05'), asset=asset_hf1,
        base_asset=asset_krw, granularity=Granularity.day, close=450195)

    db.session.delete(portfolio)
    db.session.commit()


def test_portfolio_balance(account_checking, account_savings, account_sp500,
                           asset_krw, asset_sp500):
    """Ensures a portfolio, which is essentially a collection of accounts,
    calculates its balance correctly.
    """
    portfolio = Portfolio()
    portfolio.base_asset = asset_krw
    portfolio.add_accounts(account_checking, account_savings, account_sp500)

    assert portfolio.balance(parse_date('2016-05-20')) == {}

    deposit(account_checking, asset_krw, 1500, parse_date('2016-05-01'))
    deposit(account_savings, asset_krw, 3000, parse_date('2016-05-01'))
    deposit(account_sp500, asset_sp500, 120, parse_date('2016-05-01'))

    assert portfolio.balance(parse_date('2016-05-20')) \
        == {asset_krw: 4500, asset_sp500: 120}

    deposit(account_savings, asset_krw, 4000, parse_date('2016-05-02'))
    deposit(account_savings, asset_krw, 5000, parse_date('2016-05-03'))

    assert portfolio.balance(parse_date('2016-05-20')) \
        == {asset_krw: 13500, asset_sp500: 120}

    balance_adjustment(
        account_savings, asset_krw, 10000, parse_date('2016-05-04'))

    assert portfolio.balance(parse_date('2016-05-20')) \
        == {asset_krw: 11500, asset_sp500: 120}

    db.session.delete(portfolio)
    db.session.commit()


def test_transaction():
    with Transaction.create() as t:
        assert t.state == TransactionState.initiated
    assert t.state == TransactionState.closed

    t = Transaction.create()
    assert t.state == TransactionState.initiated
    t.close(closed_at=datetime.utcnow())
    assert t.state == TransactionState.closed


def test_records(account_checking, asset_krw):
    with Transaction.create() as t:
        record = deposit(account_checking, asset_krw, 1000,
                         parse_date('2016-03-14'), t)

        # Make sure the record type has been set implictly
        assert RecordType.deposit == record.type

    with Transaction.create() as t:
        record = deposit(account_checking, asset_krw, -2000,
                         parse_date('2016-03-14'), t)

        # Make sure the record type has been set implictly
        assert RecordType.withdraw == record.type

    with Transaction.create() as t:
        record = balance_adjustment(
            account_checking, asset_krw, 3000, parse_date('2016-03-14'), t)

        # Make sure the record type has been set explicitly
        assert RecordType.balance_adjustment == record.type


def test_record_created_at(account_checking, asset_krw):
    record = deposit(account_checking, asset_krw, 1000)

    # `created_at` must be set as the time at which the record created
    assert record.created_at


def test_net_worth_without_asset_value(request, account_sp500, asset_krw,
                                       asset_sp500):
    asset_values = AssetValue.query.filter_by(asset=asset_sp500)
    for asset_value in asset_values:
        db.session.delete(asset_value)
    db.session.commit()

    record = deposit(account_sp500, asset_sp500, 1000, parse_date('2016-05-27'))

    with pytest.raises(AssetValueUnavailableException):
        account_sp500.net_worth(parse_date('2016-05-28'), base_asset=asset_krw)

    def teardown():
        db.session.delete(record)
        db.session.commit()
    request.addfinalizer(teardown)


def test_account_net_worth_1(account_checking, asset_krw):
    assert 0 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-01'), base_asset=asset_krw)
    assert 0 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-02'), base_asset=asset_krw)
    assert 0 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-03'), base_asset=asset_krw)
    assert 0 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-04'), base_asset=asset_krw)

    with Transaction.create() as t:
        deposit(account_checking, asset_krw, 1000, parse_date('2016-01-01'), t)

    assert 1000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-01'), base_asset=asset_krw)
    assert 1000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-02'), base_asset=asset_krw)
    assert 1000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-03'), base_asset=asset_krw)
    assert 1000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-04'), base_asset=asset_krw)

    with Transaction.create() as t:
        deposit(account_checking, asset_krw, 2000, parse_date('2016-01-02'), t)

    assert 1000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-01'), base_asset=asset_krw)
    assert 3000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-02'), base_asset=asset_krw)
    assert 3000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-03'), base_asset=asset_krw)
    assert 3000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-04'), base_asset=asset_krw)

    with Transaction.create() as t:
        deposit(account_checking, asset_krw, -1500, parse_date('2016-01-03'), t)

    assert 1000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-01'), base_asset=asset_krw)
    assert 3000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-02'), base_asset=asset_krw)
    assert 1500 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-03'), base_asset=asset_krw)
    assert 1500 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-04'), base_asset=asset_krw)


def test_account_net_worth_2(account_checking, account_sp500, asset_krw, asset_sp500):
    AssetValue.create(
        evaluated_at=parse_date('2016-02-25'), asset=asset_sp500,
        base_asset=asset_krw, granularity=Granularity.day, close=921.77)
    AssetValue.create(
        evaluated_at=parse_date('2016-02-24'), asset=asset_sp500,
        base_asset=asset_krw, granularity=Granularity.day, close=932.00)
    AssetValue.create(
        evaluated_at=parse_date('2016-02-23'), asset=asset_sp500,
        base_asset=asset_krw, granularity=Granularity.day, close=921.06)
    AssetValue.create(
        evaluated_at=parse_date('2016-02-22'), asset=asset_sp500,
        base_asset=asset_krw, granularity=Granularity.day, close=921.76)

    with Transaction.create() as t:
        deposit(account_sp500, asset_sp500, 1000, parse_date('2016-02-25'), t)
        deposit(account_checking, asset_krw, -1000 * 921.77,
                parse_date('2016-02-25'), t)

    assert 921770 == account_sp500.net_worth(
        evaluated_at=parse_date('2016-02-25'), base_asset=asset_krw)

    assert 921770 == account_sp500.net_worth(
        evaluated_at=parse_date('2016-03-01'), approximation=True,
        base_asset=asset_krw)


def test_account_net_worth_3(account_checking, asset_usd):
    """Ensures Account.net_worth() works with implicit `created_at`, which is
    the current datetime.
    """
    deposit(account_checking, asset_usd, 1000)

    net_worth = account_checking.net_worth(
        base_asset=asset_usd)
    assert net_worth == 1000

def test_account_net_worth_4(account_checking, asset_usd):
    """Ensures Account.net_worth() works with explicit `created_at`."""
    deposit(account_checking, asset_usd, 1000,
            parse_datetime('2018-08-30 23:00:00'))

    net_worth = account_checking.net_worth(
        base_asset=asset_usd, evaluated_at=parse_date('2018-08-30'))
    assert net_worth == 1000


def test_granularity_enum():
    assert Granularity.sec
    assert Granularity.min
    assert Granularity.five_min
    assert Granularity.hour
    assert Granularity.day
    assert Granularity.week
    assert Granularity.month
    assert Granularity.year

    with pytest.raises(AttributeError):
        Granularity.nano_sec


def test_valid_granularity():
    values = (
        Granularity.sec,
        Granularity.min,
        Granularity.five_min,
        Granularity.hour,
        Granularity.day,
        Granularity.week,
        Granularity.month,
        Granularity.year,
    )
    for value in values:
        assert Granularity.is_valid(value)


def test_invalid_granularity():
    assert not Granularity.is_valid(None)
    assert not Granularity.is_valid('invalid')


def test_transaction_state_enum():
    assert TransactionState.initiated
    assert TransactionState.closed
    assert TransactionState.pending
    assert TransactionState.invalid

    with pytest.raises(AttributeError):
        TransactionState.error


def test_record_type_enum():
    assert RecordType.deposit
    assert RecordType.withdraw
    assert RecordType.balance_adjustment

    with pytest.raises(AttributeError):
        RecordType.steal
