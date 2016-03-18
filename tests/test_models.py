import pytest

from finance.models import *  # noqa
from finance.utils import make_date


def test_asset_values(account_hf, asset_hf1):
    pass


def test_transaction(app):
    with app.app_context():
        with Transaction.create() as t:
            t.state = 'xxxx'


def test_records(app, account_checking, asset_krw):
    with app.app_context():
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


def test_net_worth(app, account_checking, account_sp500, asset_krw,
                   asset_sp500):
    with app.app_context():
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

        net_worth = account_sp500.net_worth(make_date('2016-02-25'))

        # The account only has one type of asset
        assert 1 == len(net_worth)
        assert 921770 == net_worth[asset_sp500]

        net_worth = account_sp500.net_worth(make_date('2016-03-01'),
                                            approximation=True)
        assert 921770 == net_worth[asset_sp500]

        with pytest.raises(AssetValueUnavailableException):
            net_worth = account_sp500.net_worth(make_date('2016-03-01'))
