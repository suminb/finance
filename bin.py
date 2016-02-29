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
                account=account_checking, asset=asset_krw,
                quantity=1000000)
        with Transaction.create() as t:
            Record.create(
                transaction=t,
                account=account_checking, asset=asset_krw,
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


@cli.command()
def test():
    app = create_app(__name__)
    with app.app_context():
        with Transaction.create() as t:
            t.state = 'xxxx'

if __name__ == '__main__':
    cli()
