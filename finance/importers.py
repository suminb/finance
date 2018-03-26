"""A collection of data import functions."""
import csv
import io
from datetime import timedelta

from sqlalchemy.exc import IntegrityError

from finance import log
from finance.models import (Account, Asset, AssetValue, Granularity, Record,
                            Transaction, db)
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


def synthesize_datetime(datetime, seq):
    """The original CSV file does not include time information (it only
    includes date) and there is a high probability of having multiple records
    on a single day.  However, we have a unique constraint on (account_id,
    asset_id, created_at, quantity) fields on the Record model. In order to
    circumvent potential clashes, we are adding up some seconds (with the
    sequence value) on the original timestamp.
    """
    return datetime + timedelta(seconds=seq)


def make_single_record_transaction(created_at, account, asset, quantity):
    """Creates a single record transaction (e.g., a deposit)"""
    return Record.create(
        account_id=account.id,
        asset_id=asset.id,
        created_at=created_at,
        quantity=quantity,
    )


def make_double_record_transaction(
    created_at, account, asset_from, quantity_from, asset_to, quantity_to
):
    """Creates a double record transaction (e.g., a buy order of stocks)"""
    with Transaction.create() as t:
        record1 = Record.create(
            transaction=t,
            account_id=account.id,
            asset_id=asset_from.id,
            created_at=created_at,
            quantity=quantity_from,
        )
        record2 = Record.create(
            transaction=t,
            account_id=account.id,
            asset_id=asset_to.id,
            created_at=created_at,
            quantity=quantity_to,
        )
    return (record1, record2)


def import_miraeasset_foreign_records(
    fin: io.TextIOWrapper,
    account: Account,
):
    provider = Miraeasset()
    asset_krw = Asset.get_by_symbol('KRW')

    for r in provider.parse_foreign_transactions(fin):
        assert r.currency != 'KRW'
        # FIXME: Handle a case where asset cannot be found
        target_asset = Asset.get_by_symbol(r.currency)

        if r.category == '해외주매수':
            asset_stock = Asset.get_by_isin(r.code)
            make_double_record_transaction(
                synthesize_datetime(r.created_at, r.seq),
                account,
                target_asset, -r.amount,
                asset_stock, r.quantity)
        elif r.category == '해외주매도':
            asset_stock = Asset.get_by_isin(r.code)
            make_double_record_transaction(
                synthesize_datetime(r.created_at, r.seq),
                account,
                asset_stock, -r.quantity,
                target_asset, r.amount)
        elif r.category == '해외주배당금':
            make_single_record_transaction(
                synthesize_datetime(r.created_at, r.seq),
                account, target_asset, r.amount)
        elif r.category == '환전매수':
            local_amount = int(r.raw_columns[6])  # amount in KRW
            make_double_record_transaction(
                synthesize_datetime(r.created_at, r.seq),
                account,
                asset_krw, -local_amount,
                target_asset, r.amount)
        elif r.category == '환전매도':
            raise NotImplementedError
        elif r.category == '외화인지세':
            make_single_record_transaction(
                synthesize_datetime(r.created_at, r.seq),
                account, target_asset, -r.amount)
        else:
            raise ValueError('Unknown record category: {0}'.format(r.category))
