"""A collection of data import functions."""
import csv
import io
from datetime import timedelta

from sqlalchemy.exc import IntegrityError

from finance import log
from finance.models import (Account, Asset, AssetValue, Granularity, Record,
                            RecordType, Transaction, db)
from finance.providers import Miraeasset


# NOTE: A verb 'import' means local structured data -> database
def import_stock_values(fin: io.TextIOWrapper, code: str, base_asset=None):
    """Import stock values."""
    asset = Asset.get_by_symbol(code)
    reader = csv.reader(
        fin, delimiter=',', quotechar='"', skipinitialspace=True)
    for date, open_, high, low, close_, volume, source in reader:
        try:
            AssetValue.create(
                evaluated_at=date, granularity=Granularity.day, asset=asset,
                base_asset=base_asset, open=open_, high=high, low=low,
                close=close_, volume=volume, source=source)
        except IntegrityError:
            log.warn('AssetValue for {0} on {1} already exist', code, date)
            db.session.rollback()


def import_miraeasset_foreign_records(
    fin: io.TextIOWrapper,
    account: Account,
):
    provider = Miraeasset()
    asset_usd = Asset.get_by_symbol('USD')
    asset_krw = Asset.get_by_symbol('KRW')

    for r in provider.parse_foreign_transactions(fin):
        assert r.currency != 'KRW'

        if r.category == '해외주매수':
            asset = Asset.get_by_isin(r.code)

            # TODO: Code refactoring required
            with Transaction.create() as t:
                Record.create(
                    account_id=account.id,
                    asset_id=asset_usd.id,
                    transaction=t,
                    type=RecordType.withdraw,
                    created_at=r.created_at + timedelta(seconds=r.seq),
                    category='',
                    quantity=-r.amount,
                )
                Record.create(
                    account_id=account.id,
                    asset_id=asset.id,
                    transaction=t,
                    type=RecordType.deposit,
                    created_at=r.created_at + timedelta(seconds=r.seq),
                    category='',
                    quantity=r.quantity,
                )
        elif r.category == '해외주매도':
            with Transaction.create() as t:
                Record.create(
                    account_id=account.id,
                    asset_id=asset_usd.id,
                    transaction=t,
                    type=RecordType.deposit,
                    created_at=r.created_at + timedelta(seconds=r.seq),
                    category='',
                    quantity=r.amount,
                )
                Record.create(
                    account_id=account.id,
                    asset_id=asset.id,
                    transaction=t,
                    type=RecordType.withdraw,
                    created_at=r.created_at + timedelta(seconds=r.seq),
                    category='',
                    quantity=-r.quantity,
                )
        elif r.category == '해외주배당금':
            Record.create(
                account_id=account.id,
                asset_id=asset_usd.id,
                type=RecordType.deposit,
                created_at=r.created_at + timedelta(seconds=r.seq),
                category='',
                quantity=r.amount,
            )
        elif r.category == '환전매수':
            # FIXME: Asset may not be USD
            local_amount = int(r.raw_columns[6])  # amount in KRW
            with Transaction.create() as t:
                Record.create(
                    account_id=account.id,
                    asset_id=asset_usd.id,
                    transaction=t,
                    type=RecordType.deposit,
                    created_at=r.created_at + timedelta(seconds=r.seq),
                    category='',
                    quantity=r.amount,
                )
                Record.create(
                    account_id=account.id,
                    asset_id=asset_krw.id,
                    transaction=t,
                    type=RecordType.withdraw,
                    created_at=r.created_at + timedelta(seconds=r.seq),
                    category='',
                    quantity=-local_amount,
                )
        elif r.category == '외화인지세':
            Record.create(
                account_id=account.id,
                asset_id=asset_usd.id,
                type=RecordType.withdraw,
                created_at=r.created_at + timedelta(seconds=r.seq),
                category='',
                quantity=-r.amount,
            )
            pass
