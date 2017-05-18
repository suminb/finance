import collections
from datetime import datetime
import functools
import operator

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON
import uuid64

from finance.exceptions import (
    AssetNotFoundException, AssetValueUnavailableException,
    InvalidTargetAssetException)
from finance.utils import date_range


db = SQLAlchemy()
JsonType = db.String().with_variant(JSON(), 'postgresql')


def get_asset_by_fund_code(code: str):
    """Gets an Asset instance mapped to the given fund code.

    :param code: A fund code
    """
    # NOTE: I know this looks really stupid, but we'll stick with this
    # temporary workaround until we figure out how to create an instance of
    # Asset model from a raw query result
    # (sqlalchemy.engine.result.RowProxy)
    query = "SELECT * FROM asset WHERE data->>'code' = :code LIMIT 1"
    raw_asset = db.session.execute(query, {'code': code}).first()
    if not raw_asset:
        raise AssetNotFoundException(
            'Fund code {} is not mapped to any asset'.format(code))
    asset_id = raw_asset[0]
    return Asset.query.get(asset_id)


def get_asset_by_stock_code(code: str):
    return Asset.query.filter(Asset.code == code).first()


class CRUDMixin(object):
    """Copied from https://realpython.com/blog/python/python-web-applications-with-flask-part-ii/
    """  # noqa

    __table_args__ = {'extend_existing': True}

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=False,
                   default=uuid64.issue())

    @classmethod
    def create(cls, commit=True, **kwargs):
        if 'id' not in kwargs:
            kwargs.update(dict(id=uuid64.issue()))
        instance = cls(**kwargs)

        if hasattr(instance, 'timestamp') \
                and getattr(instance, 'timestamp') is None:
            instance.timestamp = datetime.utcnow()

        return instance.save(commit=commit)

    @classmethod
    def get(cls, id):
        return cls.query.get(id)

    # We will also proxy Flask-SqlAlchemy's get_or_404
    # for symmetry
    @classmethod
    def get_or_404(cls, id):
        return cls.query.get_or_404(id)

    @classmethod
    def exists(cls, **kwargs):
        row = cls.query.filter_by(**kwargs).first()
        return row is not None

    def update(self, commit=True, **kwargs):
        for attr, value in kwargs.iteritems():
            setattr(self, attr, value)
        return commit and self.save() or self

    def save(self, commit=True):
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    def delete(self, commit=True):
        db.session.delete(self)
        return commit and db.session.commit()

    def as_dict(self):
        def iter():
            for column in self.__table__.columns:
                yield column.name, str(getattr(self, column.name))

        return {k: v for k, v in iter()}


class User(CRUDMixin, UserMixin, db.Model):

    given_name = db.Column(db.String)
    family_name = db.Column(db.String)
    email = db.Column(db.String, unique=True)

    #: Arbitrary data
    data = db.Column(JsonType)

    accounts = db.relationship('Account', backref='user', lazy='dynamic')

    def __repr__(self):
        return 'User <{}>'.format(self.name)

    @property
    def name(self):
        # TODO: i18n
        return u'{}, {}'.format(self.family_name, self.given_name)


# TODO: Need a way to keep track of the value of volatile assets such as stocks
# TODO: Need a way to convert one asset's value to another (e.g., currency
# conversion, stock evaluation, etc.)


class Granularity(object):
    sec = '1sec'
    min = '1min'
    five_min = '5min'
    hour = '1hour'
    day = '1day'
    week = '1week'
    month = '1month'
    year = '1year'

    def is_valid(self, value):
        raise NotImplementedError


class AssetValue(CRUDMixin, db.Model):
    """Represents a unit price of an asset at a particular point of time. The
    granularity of the 'particular point of time' may range from one second
    to a year. See `Granularity` for more details."""

    __table_args__ = (db.UniqueConstraint(
        'asset_id', 'evaluated_at', 'granularity'), {})

    asset_id = db.Column(db.BigInteger, db.ForeignKey('asset.id'))
    base_asset_id = db.Column(db.BigInteger, db.ForeignKey('asset.id'))
    base_asset = db.relationship('Asset', uselist=False,
                                 foreign_keys=[base_asset_id])
    evaluated_at = db.Column(db.DateTime(timezone=False))
    granularity = db.Column(db.Enum('1sec', '1min', '5min', '1hour', '1day',
                                    '1week', '1month', '1year',
                                    name='granularity'))
    open = db.Column(db.Numeric(precision=20, scale=4))
    high = db.Column(db.Numeric(precision=20, scale=4))
    low = db.Column(db.Numeric(precision=20, scale=4))
    close = db.Column(db.Numeric(precision=20, scale=4))
    volume = db.Column(db.Integer)


class AssetType(object):
    currency = 'currency'
    stock = 'stock'
    bond = 'bond'
    p2p_bond = 'p2p_bond'
    security = 'security'  # NOTE: Is this necessary?
    fund = 'fund'
    commodity = 'commodity'


asset_types = (
    AssetType.currency, AssetType.stock, AssetType.bond, AssetType.p2p_bond,
    AssetType.security, AssetType.fund, AssetType.commodity)


class Asset(CRUDMixin, db.Model):
    """Represents an asset."""

    type = db.Column(db.Enum(*asset_types, name='asset_type'))
    name = db.Column(db.String)
    code = db.Column(db.String)
    description = db.Column(db.Text)

    #: Arbitrary data
    data = db.Column(JsonType)

    asset_values = db.relationship(
        'AssetValue', backref='asset', foreign_keys=[AssetValue.asset_id],
        lazy='dynamic', cascade='all,delete-orphan')
    base_asset_values = db.relationship(
        'AssetValue', foreign_keys=[AssetValue.base_asset_id],
        lazy='dynamic', cascade='all,delete-orphan')
    records = db.relationship('Record', backref='asset',
                              lazy='dynamic', cascade='all,delete-orphan')

    def __repr__(self):
        name = self.code if self.code is not None else self.name
        return 'Asset <{} ({})>'.format(name, self.description)

    @property
    def unit_price(self):
        raise NotImplementedError

    @property
    def current_value(self):
        raise NotImplementedError

    #
    # P2P bonds only features
    #
    def is_delayed(self):
        raise NotImplementedError

    def is_defaulted(self):
        raise NotImplementedError

    def last_payment(self):
        raise NotImplementedError

    def principle(self):
        return self.asset_values \
            .order_by(AssetValue.evaluated_at).first().close

    def returned_principle(self):
        now = datetime.now()
        return self.asset_values.filter(AssetValue.evaluated_at <= now) \
            .order_by(AssetValue.evaluated_at.desc()).first().close
    #
    # End of P2P bonds only features
    #


class Account(CRUDMixin, db.Model):
    """Represents an account. An account may contain multiple records based
    on different assets. For example, a single bank account may have a balance
    in different foreign currencies."""

    user_id = db.Column(db.BigInteger, db.ForeignKey('user.id'))
    portfolio_id = db.Column(db.BigInteger, db.ForeignKey('portfolio.id'))
    type = db.Column(db.Enum('checking', 'savings', 'investment',
                             'credit_card', 'virtual', name='account_type'))
    name = db.Column(db.String)
    number = db.Column(db.String)  # Account number
    description = db.Column(db.Text)

    #: Arbitrary data
    data = db.Column(JsonType)

    # NOTE: Transaction-Account relationship is many-to-many
    # transactions = db.relationship('Transaction', backref='account',
    #                                lazy='dynamic')
    records = db.relationship('Record', backref='account',
                              lazy='dynamic')

    def __repr__(self):
        return 'Account <{} ({})>'.format(self.name, self.type)

    def balance(self, evaluated_at=None):
        """Calculates the account balance on a given date."""
        if not evaluated_at:
            evaluated_at = datetime.utcnow()

        # FIMXE: Consider open transactions
        records = Record.query \
            .filter(
                Record.account == self,
                Record.created_at <= evaluated_at) \
            .order_by(
                Record.created_at)

        # Sum all transactions to produce {asset: sum(quantity)} dictionary
        bs = {}
        rs = [(r.asset, r.quantity, r.type) for r in records]
        for asset, quantity, type in rs:
            bs.setdefault(asset, 0)
            if type == RecordType.balance_adjustment:
                # Previous records will be ignored when 'balance_adjustment'
                # is seen.
                bs[asset] = quantity
            else:
                bs[asset] += quantity
        return bs

    def net_worth(self, evaluated_at=None, granularity=Granularity.day,
                  approximation=False, base_asset=None):
        """Calculates the net worth of the account on a particular datetime.
        If approximation=True and the asset value record is unavailable for the
        given date (evaluated_at), try to pull the most recent AssetValue.
        """
        if base_asset is None:
            raise InvalidTargetAssetException('Base asset cannot be null')

        if not evaluated_at:
            evaluated_at = datetime.utcnow()

        if granularity == Granularity.day:
            if isinstance(evaluated_at, datetime):
                # NOTE: Any better way to handle this?
                date = evaluated_at.date().timetuple()[:6]
                evaluated_at = datetime(*date)
        else:
            raise NotImplementedError

        net_asset_value = 0
        for asset, quantity in self.balance(evaluated_at).items():
            if asset == base_asset:
                net_asset_value += quantity
                continue

            asset_value = AssetValue.query \
                .filter(AssetValue.asset == asset,
                        AssetValue.granularity == granularity,
                        AssetValue.base_asset == base_asset)
            if approximation:
                asset_value = asset_value.filter(
                    AssetValue.evaluated_at <= evaluated_at) \
                    .order_by(AssetValue.evaluated_at.desc())
            else:
                asset_value = asset_value.filter(
                    AssetValue.evaluated_at == evaluated_at)

            asset_value = asset_value.first()

            if asset_value:
                worth = asset_value.close * quantity
            else:
                raise AssetValueUnavailableException()
            net_asset_value += worth

        return net_asset_value


class Portfolio(CRUDMixin, db.Model):
    """A collection of accounts (= a collection of assets)."""
    __table_args__ = (
        db.ForeignKeyConstraint(['base_asset_id'], ['asset.id']),
    )
    name = db.Column(db.String)
    description = db.Column(db.String)
    accounts = db.relationship('Account', backref='portfolio', lazy='dynamic')
    base_asset_id = db.Column(db.BigInteger)
    base_asset = db.relationship('Asset', uselist=False,
                                 foreign_keys=[base_asset_id])

    def add_accounts(self, *accounts, commit=True):
        self.accounts.extend(accounts)
        if commit:
            db.session.commit()

    def balance(self, evaluated_at=None):
        """Calculates the sum of all account balances on a given date."""
        if not evaluated_at:
            evaluated_at = datetime.utcnow()

        # Balances of all accounts under this portfolio
        bs = [account.balance(evaluated_at) for account in self.accounts]

        return functools.reduce(operator.add, map(collections.Counter, bs))

    def net_worth(self, evaluated_at=None, granularity=Granularity.day):
        """Calculates the net worth of the portfolio on a particular datetime.
        """
        net = 0
        for account in self.accounts:
            net += account.net_worth(evaluated_at, granularity, True,
                                     self.base_asset)
        return net

    def daily_net_worth(self, date_from, date_to, granularity=Granularity.day):
        """NOTE: This probably shouldn't be here, but we'll leave it here for
        demonstration purposes.
        """
        # FIXME: Calculate the daily net worth incrementally
        for date in date_range(date_from, date_to):
            yield date, self.net_worth(date)


class TransactionState(object):
    initiated = 'initiated'
    closed = 'closed'
    pending = 'pending'
    invalid = 'invalid'


transaction_states = (
    TransactionState.initiated, TransactionState.closed,
    TransactionState.pending, TransactionState.invalid)


class Transaction(CRUDMixin, db.Model):
    """A transaction consists of multiple records."""
    initiated_at = db.Column(db.DateTime(timezone=False))
    closed_at = db.Column(db.DateTime(timezone=False))
    state = db.Column(db.Enum(*transaction_states, name='transaction_state'))
    #: Individual record
    records = db.relationship('Record', backref='transaction',
                              lazy='dynamic')

    def __init__(self, initiated_at=None, *args, **kwargs):
        if initiated_at:
            self.initiated_at = initiated_at
        else:
            self.initiated_at = datetime.utcnow()
        self.state = TransactionState.initiated
        super(self.__class__, self).__init__(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        """Implicitly mark the transaction as closed only if the state is
        'initiated'."""
        if self.state == TransactionState.initiated:
            self.close()

    def close(self, closed_at=None, commit=True):
        """Explicitly close a transaction."""
        if closed_at:
            self.closed_at = closed_at
        else:
            self.closed_at = datetime.utcnow()
        self.state = TransactionState.closed

        if commit:
            db.session.commit()


class RecordType(object):
    deposit = 'deposit'
    withdraw = 'withdraw'
    balance_adjustment = 'balance_adjustment'


record_types = (RecordType.deposit, RecordType.withdraw,
                RecordType.balance_adjustment)


class Record(CRUDMixin, db.Model):
    """A financial transaction consists of one or more records."""

    # NOTE: Is this okay to do this?
    __table_args__ = (db.UniqueConstraint(
        'account_id', 'asset_id', 'created_at', 'quantity'), {})

    account_id = db.Column(db.BigInteger, db.ForeignKey('account.id'))
    asset_id = db.Column(db.BigInteger, db.ForeignKey('asset.id'))
    # asset = db.relationship(Asset, uselist=False)
    transaction_id = db.Column(db.BigInteger, db.ForeignKey('transaction.id'))
    type = db.Column(db.Enum(*record_types, name='record_type'))
    # NOTE: We'll always use the UTC time
    created_at = db.Column(db.DateTime(timezone=False))
    category = db.Column(db.String)
    quantity = db.Column(db.Numeric(precision=20, scale=4))

    def __init__(self, *args, **kwargs):
        # Record.type could be 'balance_adjustment'
        if 'type' not in kwargs and 'quantity' in kwargs:
            if kwargs['quantity'] < 0:
                kwargs['type'] = RecordType.withdraw
            else:
                kwargs['type'] = RecordType.deposit
        super(self.__class__, self).__init__(*args, **kwargs)


class DartReport(CRUDMixin, db.Model):
    """NOTE: We need a more generic name for this..."""

    registered_at = db.Column(db.DateTime(timezone=False))
    title = db.Column(db.String)
    entity = db.Column(db.String)
    reporter = db.Column(db.String)
    content = db.Column(db.Text)
