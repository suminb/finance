import pytest

from finance.models import *  # noqa
from finance.utils import make_date


def test_portfolio(account_hf, asset_hf1, account_checking, asset_krw):
    portfolio = Portfolio()
    portfolio.target_asset = asset_krw
    portfolio.add_accounts(account_hf, account_checking)

    with Transaction.create() as t:
        Record.create(
            created_at=make_date('2015-12-04'), transaction=t,
            account=account_checking, asset=asset_krw, quantity=500000)
        Record.create(
            created_at=make_date('2015-12-04'), transaction=t,
            account=account_checking, asset=asset_krw, quantity=-500000)
        Record.create(
            created_at=make_date('2015-12-04'), transaction=t,
            account=account_hf, asset=asset_hf1, quantity=1)

    net_worth = portfolio.net_worth(evaluated_at=make_date('2015-12-04'),
                                    granularity=Granularity.day)
    # The net asset value shall be initially zero
    assert 0 == net_worth

    # Initial asset value
    AssetValue.create(
        evaluated_at=make_date('2015-12-04'), asset=asset_hf1,
        target_asset=asset_krw, granularity='1day', close=500000)

    net_worth = portfolio.net_worth(evaluated_at=make_date('2015-12-04'),
                                    granularity=Granularity.day)
    assert 500000 == net_worth

    # 1st payment
    interest, tax, returned = 3923, 740, 30930
    with Transaction.create() as t:
        Record.create(
            created_at=make_date('2016-01-08'), transaction=t,
            account=account_checking, asset=asset_krw, quantity=returned)
    # Remaining principle value after the 1st payment
    AssetValue.create(
        evaluated_at=make_date('2016-01-08'), asset=asset_hf1,
        target_asset=asset_krw, granularity='1day', close=472253)

    net_worth = portfolio.net_worth(evaluated_at=make_date('2016-01-08'),
                                    granularity=Granularity.day)
    assert 500000 + (interest - tax) == net_worth

    # 2nd payment
    with Transaction.create() as t:
        Record.create(
            created_at=make_date('2016-02-05'), transaction=t,
            account=account_checking, asset=asset_krw, quantity=25016)
    # Remaining principle value after the 2nd payment
    AssetValue.create(
        evaluated_at=make_date('2016-02-05'), asset=asset_hf1,
        target_asset=asset_krw, granularity='1day', close=450195)

    db.session.delete(portfolio)
    db.session.commit()


def _test_transaction():
    with Transaction.create() as t:
        t.state = 'xxxx'


def test_records(account_checking, asset_krw):
    with Transaction.create() as t:
        record = Record.create(
            created_at=make_date('2016-03-14'), transaction=t,
            account=account_checking, asset=asset_krw,
            quantity=1000)

        # Make sure the record type has been set implictly
        assert 'deposit' == record.type

    with Transaction.create() as t:
        record = Record.create(
            created_at=make_date('2016-03-14'), transaction=t,
            account=account_checking, asset=asset_krw,
            quantity=-2000)

        # Make sure the record type has been set implictly
        assert 'withdraw' == record.type

    with Transaction.create() as t:
        record = Record.create(
            created_at=make_date('2016-03-14'), transaction=t,
            account=account_checking, asset=asset_krw,
            quantity=3000, type='balance_adjustment')

        # Make sure the record type has been set explicitly
        assert 'balance_adjustment' == record.type


def test_net_worth_1(account_checking, asset_krw):
    assert 0 == account_checking.net_worth(
        evaluated_at=make_date('2016-01-01'), target_asset=asset_krw)
    assert 0 == account_checking.net_worth(
        evaluated_at=make_date('2016-01-02'), target_asset=asset_krw)
    assert 0 == account_checking.net_worth(
        evaluated_at=make_date('2016-01-03'), target_asset=asset_krw)
    assert 0 == account_checking.net_worth(
        evaluated_at=make_date('2016-01-04'), target_asset=asset_krw)

    with Transaction.create() as t:
        Record.create(
            created_at=make_date('2016-01-01'), transaction=t,
            account=account_checking, asset=asset_krw, quantity=1000)

    assert 1000 == account_checking.net_worth(
        evaluated_at=make_date('2016-01-01'), target_asset=asset_krw)
    assert 1000 == account_checking.net_worth(
        evaluated_at=make_date('2016-01-02'), target_asset=asset_krw)
    assert 1000 == account_checking.net_worth(
        evaluated_at=make_date('2016-01-03'), target_asset=asset_krw)
    assert 1000 == account_checking.net_worth(
        evaluated_at=make_date('2016-01-04'), target_asset=asset_krw)

    with Transaction.create() as t:
        Record.create(
            created_at=make_date('2016-01-02'), transaction=t,
            account=account_checking, asset=asset_krw, quantity=2000)

    assert 1000 == account_checking.net_worth(
        evaluated_at=make_date('2016-01-01'), target_asset=asset_krw)
    assert 3000 == account_checking.net_worth(
        evaluated_at=make_date('2016-01-02'), target_asset=asset_krw)
    assert 3000 == account_checking.net_worth(
        evaluated_at=make_date('2016-01-03'), target_asset=asset_krw)
    assert 3000 == account_checking.net_worth(
        evaluated_at=make_date('2016-01-04'), target_asset=asset_krw)

    with Transaction.create() as t:
        Record.create(
            created_at=make_date('2016-01-03'), transaction=t,
            account=account_checking, asset=asset_krw, quantity=-1500)

    assert 1000 == account_checking.net_worth(
        evaluated_at=make_date('2016-01-01'), target_asset=asset_krw)
    assert 3000 == account_checking.net_worth(
        evaluated_at=make_date('2016-01-02'), target_asset=asset_krw)
    assert 1500 == account_checking.net_worth(
        evaluated_at=make_date('2016-01-03'), target_asset=asset_krw)
    assert 1500 == account_checking.net_worth(
        evaluated_at=make_date('2016-01-04'), target_asset=asset_krw)


def test_net_worth_2(account_checking, account_sp500, asset_krw, asset_sp500):
    AssetValue.create(
        evaluated_at=make_date('2016-02-25'), asset=asset_sp500,
        target_asset=asset_krw, granularity='1day', close=921.77)
    AssetValue.create(
        evaluated_at=make_date('2016-02-24'), asset=asset_sp500,
        target_asset=asset_krw, granularity='1day', close=932.00)
    AssetValue.create(
        evaluated_at=make_date('2016-02-23'), asset=asset_sp500,
        target_asset=asset_krw, granularity='1day', close=921.06)
    AssetValue.create(
        evaluated_at=make_date('2016-02-22'), asset=asset_sp500,
        target_asset=asset_krw, granularity='1day', close=921.76)

    with Transaction.create() as t:
        Record.create(
            created_at=make_date('2016-02-25'), transaction=t,
            account=account_sp500, asset=asset_sp500,
            quantity=1000)
        Record.create(
            created_at=make_date('2016-02-25'), transaction=t,
            account=account_checking, asset=asset_krw,
            quantity=-1000 * 921.77)

    assert 921770 == account_sp500.net_worth(
        evaluated_at=make_date('2016-02-25'), target_asset=asset_krw)

    assert 921770 == account_sp500.net_worth(
        evaluated_at=make_date('2016-03-01'), approximation=True,
        target_asset=asset_krw)

    with pytest.raises(AssetValueUnavailableException):
        account_sp500.net_worth(make_date('2016-03-01'),
                                target_asset=asset_krw)
