from finance.models import *  # noqa


def make_date(strdate):
    """Make a datetime object from a string.

    :type strdate: str
    """
    return datetime.strptime(strdate, '%Y-%m-%d')


def test_transaction(app):
    app = create_app(__name__)
    with app.app_context():
        with Transaction.create() as t:
            t.state = 'xxxx'


def test_net_worth(app, db):
    with app.app_context():
        account_checking = Account.create(
            type='checking', name='Shinhan Checking')
        account_sp500 = Account.create(
            type='investment', name='S&P500 Fund')

        asset_krw = Asset.create(
            type='currency', name='KRW', description='Korean Won')
        asset_sp500 = Asset.create(
            type='security', name='S&P 500', description='')

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
