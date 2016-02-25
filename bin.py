import click

from finance import create_app
from finance.models import *  # noqa


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
        account = Account.create(
            type='checking', name='Shinhan Checking', user=user)
        asset_krw = Asset.create(
            type='currency', name='KRW', description='Korean Won')
        Transaction.create(
            account=account, state='closed', asset=asset_krw, quantity=10000)
        Transaction.create(
            account=account, state='closed', asset=asset_krw, quantity=-4900)


if __name__ == '__main__':
    cli()
