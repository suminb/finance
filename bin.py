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

        Record.create(
            account=account_checking, asset=asset_krw,
            quantity=1000000)
        Record.create(
            account=account_checking, asset=asset_krw,
            quantity=-4900)

        t1 = Transaction.create()
        Record.create(
            created_at=tf('2015-07-24'), transaction=t1,
            account=account_gold, asset=asset_gold,
            quantity=2.00)
        Record.create(
            created_at=tf('2015-07-24'), transaction=t1,
            account=account_checking, asset=asset_krw,
            quantity=-84000)
        t1.close()

        t2 = Transaction.create()
        Record.create(
            created_at=tf('2015-12-28'), transaction=t2,
            account=account_gold, asset=asset_gold,
            quantity=-1.00)
        Record.create(
            created_at=tf('2015-12-28'), transaction=t2,
            account=account_checking, asset=asset_krw,
            quantity=49000)
        t2.close()


if __name__ == '__main__':
    cli()
