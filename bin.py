from datetime import datetime

import click

from finance import create_app
from finance.models import *  # noqa


tf = lambda x: datetime.strptime(x, '%Y-%m-%d')


@click.group()
def cli():
    pass


@cli.command()
def create_all():
    app = create_app(__name__)
    with app.app_context():
        db.create_all()


@cli.command()
def drop_all():
    app = create_app(__name__)
    with app.app_context():
        db.drop_all()


@cli.command()
def insert_test_data():
    app = create_app(__name__)
    with app.app_context():
        user = User.create(
            family_name='Byeon', given_name='Sumin', email='suminb@gmail.com')

        account_checking = Account.create(
            type='checking', name='Shinhan Checking', user=user)
        account_gold = Account.create(
            type='investment', name='Woori Gold Banking', user=user)
        account_sp500 = Account.create(
            type='investment', name='S&P500 Fund', user=user)

        asset_krw = Asset.create(
            type='currency', name='KRW', description='Korean Won')
        asset_usd = Asset.create(
            type='currency', name='USD', description='United States Dollar')
        asset_gold = Asset.create(
            type='commodity', name='Gold', description='')
        asset_sp500 = Asset.create(
            type='security', name='S&P 500', description='')

        with Transaction.create() as t:
            Record.create(
                transaction=t,
                account=account_checking, asset=asset_krw, quantity=1000000)
        with Transaction.create() as t:
            Record.create(
                transaction=t, account=account_checking, asset=asset_krw,
                quantity=-4900)

        with Transaction.create() as t:
            Record.create(
                created_at=tf('2015-07-24'), transaction=t,
                account=account_gold, asset=asset_gold,
                quantity=2.00)
            Record.create(
                created_at=tf('2015-07-24'), transaction=t,
                account=account_checking, asset=asset_krw,
                quantity=-84000)

        with Transaction.create() as t:
            Record.create(
                created_at=tf('2015-12-28'), transaction=t,
                account=account_gold, asset=asset_gold,
                quantity=-1.00)
            Record.create(
                created_at=tf('2015-12-28'), transaction=t,
                account=account_checking, asset=asset_krw,
                quantity=49000)

        with Transaction.create() as t:
            Record.create(
                created_at=tf('2016-02-25'), transaction=t,
                account=account_sp500, asset=asset_sp500,
                quantity=1000)
            Record.create(
                created_at=tf('2016-02-25'), transaction=t,
                account=account_checking, asset=asset_krw,
                quantity=-1000 * 921.77)

        AssetValue.create(
            evaluated_at=tf('2016-02-25'), asset=asset_sp500,
            target_asset=asset_krw, granularity='1day', close=921.77)
        AssetValue.create(
            evaluated_at=tf('2016-02-24'), asset=asset_sp500,
            target_asset=asset_krw, granularity='1day', close=932.00)
        AssetValue.create(
            evaluated_at=tf('2016-02-23'), asset=asset_sp500,
            target_asset=asset_krw, granularity='1day', close=921.06)
        AssetValue.create(
            evaluated_at=tf('2016-02-22'), asset=asset_sp500,
            target_asset=asset_krw, granularity='1day', close=921.76)


        data = """
2016-01-22, account_gold, asset_gold, 10.00
2016-01-22, account_checking, asset_krw, -426870
2016-02-12, account_gold, asset_gold, -1.04
2016-02-12, account_checking, asset_krw, 49586
2016-02-12, account_gold, asset_gold, -1.04
2016-02-12, account_checking, asset_krw, 49816
2016-02-19, account_gold, asset_gold, -1.00
2016-02-19, account_checking, asset_krw, 48603
2016-02-23, account_gold, asset_gold, -2.08
2016-02-23, account_checking, asset_krw, 99577
2016-02-24, account_gold, asset_gold, -2.06
2016-02-24, account_checking, asset_krw, 99667
2016-02-26, account_gold, asset_gold, -1.63
2016-02-26, account_checking, asset_krw, 79589
"""


@cli.command()
def test():
    app = create_app(__name__)
    with app.app_context():
        account = Account.query.filter(Account.name == 'S&P500 Fund').first()
        print(account.net_worth(tf('2016-02-25')))

if __name__ == '__main__':
    cli()
