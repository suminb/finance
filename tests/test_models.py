import pytest

from finance.exceptions import *  # noqa
from finance.models import *  # noqa
from finance.utils import parse_date


def test_get_asset_by_fund_code(asset_sp500):
    asset = get_asset_by_fund_code('KR5223941018')
    assert asset.name == 'KB Star S&P500'


def test_get_asset_by_fund_code_non_existing(asset_sp500):
    with pytest.raises(AssetNotFoundException):
        get_asset_by_fund_code('non-exisiting')


def test_balance(account_checking, asset_krw, asset_usd):
    assert account_checking.balance() == {}

    Record.create(
        created_at=parse_date('2016-05-01'), account=account_checking,
        asset=asset_krw, quantity=1000)
    assert account_checking.balance(parse_date('2016-05-19')) \
        == {asset_krw: 1000}

    Record.create(
        created_at=parse_date('2016-05-02'), account=account_checking,
        asset=asset_krw, quantity=-500)
    assert account_checking.balance(parse_date('2016-05-19')) \
        == {asset_krw: 500}

    Record.create(
        created_at=parse_date('2016-05-03'), account=account_checking,
        asset=asset_usd, quantity=25)
    assert account_checking.balance(parse_date('2016-05-19')) \
        == {asset_krw: 500, asset_usd: 25}

    Record.create(
        created_at=parse_date('2016-05-04'), account=account_checking,
        asset=asset_usd, quantity=40, type=RecordType.balance_adjustment)
    assert account_checking.balance(parse_date('2016-05-19')) \
        == {asset_krw: 500, asset_usd: 40}


def test_portfolio(account_hf, asset_hf1, account_checking, asset_krw):
    portfolio = Portfolio()
    portfolio.base_asset = asset_krw
    portfolio.add_accounts(account_hf, account_checking)

    with Transaction.create() as t:
        Record.create(
            created_at=parse_date('2015-12-04'), transaction=t,
            account=account_checking, asset=asset_krw, quantity=500000)
        Record.create(
            created_at=parse_date('2015-12-04'), transaction=t,
            account=account_checking, asset=asset_krw, quantity=-500000)
        Record.create(
            created_at=parse_date('2015-12-04'), transaction=t,
            account=account_hf, asset=asset_hf1, quantity=1)

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
    with Transaction.create() as t:
        Record.create(
            created_at=parse_date('2016-01-08'), transaction=t,
            account=account_checking, asset=asset_krw, quantity=returned)
    # Remaining principle value after the 1st payment
    AssetValue.create(
        evaluated_at=parse_date('2016-01-08'), asset=asset_hf1,
        base_asset=asset_krw, granularity=Granularity.day, close=472253)

    net_worth = portfolio.net_worth(evaluated_at=parse_date('2016-01-08'),
                                    granularity=Granularity.day)
    assert 500000 + (interest - tax) == net_worth

    # 2nd payment
    with Transaction.create() as t:
        Record.create(
            created_at=parse_date('2016-02-05'), transaction=t,
            account=account_checking, asset=asset_krw, quantity=25016)
    # Remaining principle value after the 2nd payment
    AssetValue.create(
        evaluated_at=parse_date('2016-02-05'), asset=asset_hf1,
        base_asset=asset_krw, granularity=Granularity.day, close=450195)

    db.session.delete(portfolio)
    db.session.commit()


def test_portfolio_balance(account_checking, account_savings, account_sp500,
                           asset_krw, asset_sp500):
    portfolio = Portfolio()
    portfolio.base_asset = asset_krw
    portfolio.add_accounts(account_checking, account_savings, account_sp500)

    assert portfolio.balance(parse_date('2016-05-20')) == {}

    Record.create(
        created_at=parse_date('2016-05-01'), account=account_checking,
        asset=asset_krw, quantity=1500)
    Record.create(
        created_at=parse_date('2016-05-01'), account=account_savings,
        asset=asset_krw, quantity=3000)
    Record.create(
        created_at=parse_date('2016-05-01'), account=account_sp500,
        asset=asset_sp500, quantity=120)

    assert portfolio.balance(parse_date('2016-05-20')) \
        == {asset_krw: 4500, asset_sp500: 120}

    Record.create(
        created_at=parse_date('2016-05-02'), account=account_savings,
        asset=asset_krw, quantity=4000)
    Record.create(
        created_at=parse_date('2016-05-03'), account=account_savings,
        asset=asset_krw, quantity=5000)

    assert portfolio.balance(parse_date('2016-05-20')) \
        == {asset_krw: 13500, asset_sp500: 120}

    Record.create(
        created_at=parse_date('2016-05-04'), account=account_savings,
        asset=asset_krw, quantity=10000, type=RecordType.balance_adjustment)

    assert portfolio.balance(parse_date('2016-05-20')) \
        == {asset_krw: 11500, asset_sp500: 120}

    db.session.delete(portfolio)
    db.session.commit()


def _test_transaction():
    with Transaction.create() as t:
        t.state = 'xxxx'


def test_records(account_checking, asset_krw):
    with Transaction.create() as t:
        record = Record.create(
            created_at=parse_date('2016-03-14'), transaction=t,
            account=account_checking, asset=asset_krw,
            quantity=1000)

        # Make sure the record type has been set implictly
        assert RecordType.deposit == record.type

    with Transaction.create() as t:
        record = Record.create(
            created_at=parse_date('2016-03-14'), transaction=t,
            account=account_checking, asset=asset_krw,
            quantity=-2000)

        # Make sure the record type has been set implictly
        assert RecordType.withdraw == record.type

    with Transaction.create() as t:
        record = Record.create(
            created_at=parse_date('2016-03-14'), transaction=t,
            account=account_checking, asset=asset_krw,
            quantity=3000, type=RecordType.balance_adjustment)

        # Make sure the record type has been set explicitly
        assert RecordType.balance_adjustment == record.type


def test_net_worth_without_asset_value(request, account_sp500, asset_krw,
                                       asset_sp500):
    asset_values = AssetValue.query.filter_by(asset=asset_sp500)
    for asset_value in asset_values:
        db.session.delete(asset_value)
    db.session.commit()

    record = Record.create(
        created_at=parse_date('2016-05-27'), account=account_sp500,
        asset=asset_sp500, quantity=1000)

    with pytest.raises(AssetValueUnavailableException):
        account_sp500.net_worth(parse_date('2016-05-28'), base_asset=asset_krw)

    def teardown():
        db.session.delete(record)
        db.session.commit()
    request.addfinalizer(teardown)


def test_net_worth_1(account_checking, asset_krw):
    assert 0 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-01'), base_asset=asset_krw)
    assert 0 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-02'), base_asset=asset_krw)
    assert 0 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-03'), base_asset=asset_krw)
    assert 0 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-04'), base_asset=asset_krw)

    with Transaction.create() as t:
        Record.create(
            created_at=parse_date('2016-01-01'), transaction=t,
            account=account_checking, asset=asset_krw, quantity=1000)

    assert 1000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-01'), base_asset=asset_krw)
    assert 1000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-02'), base_asset=asset_krw)
    assert 1000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-03'), base_asset=asset_krw)
    assert 1000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-04'), base_asset=asset_krw)

    with Transaction.create() as t:
        Record.create(
            created_at=parse_date('2016-01-02'), transaction=t,
            account=account_checking, asset=asset_krw, quantity=2000)

    assert 1000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-01'), base_asset=asset_krw)
    assert 3000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-02'), base_asset=asset_krw)
    assert 3000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-03'), base_asset=asset_krw)
    assert 3000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-04'), base_asset=asset_krw)

    with Transaction.create() as t:
        Record.create(
            created_at=parse_date('2016-01-03'), transaction=t,
            account=account_checking, asset=asset_krw, quantity=-1500)

    assert 1000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-01'), base_asset=asset_krw)
    assert 3000 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-02'), base_asset=asset_krw)
    assert 1500 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-03'), base_asset=asset_krw)
    assert 1500 == account_checking.net_worth(
        evaluated_at=parse_date('2016-01-04'), base_asset=asset_krw)


def test_net_worth_2(account_checking, account_sp500, asset_krw, asset_sp500):
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
        Record.create(
            created_at=parse_date('2016-02-25'), transaction=t,
            account=account_sp500, asset=asset_sp500,
            quantity=1000)
        Record.create(
            created_at=parse_date('2016-02-25'), transaction=t,
            account=account_checking, asset=asset_krw,
            quantity=-1000 * 921.77)

    assert 921770 == account_sp500.net_worth(
        evaluated_at=parse_date('2016-02-25'), base_asset=asset_krw)

    assert 921770 == account_sp500.net_worth(
        evaluated_at=parse_date('2016-03-01'), approximation=True,
        base_asset=asset_krw)


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
