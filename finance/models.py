from datetime import datetime

from flask.ext.login import UserMixin
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON

import uuid64


db = SQLAlchemy()
JsonType = db.String().with_variant(JSON(), 'postgresql')


class CRUDMixin(object):
    """Copied from https://realpython.com/blog/python/python-web-applications-with-flask-part-ii/
    """  # noqa

    __table_args__ = {'extend_existing': True}

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=False,
                   default=uuid64.issue())

    @classmethod
    def create(cls, commit=True, **kwargs):
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


class User(db.Model, CRUDMixin, UserMixin):
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

class AssetValue(db.Model, CRUDMixin):
    __table_args__ = (db.UniqueConstraint(
        'asset_id', 'evaluated_at', 'granularity'), {})

    asset_id = db.Column(db.BigInteger, db.ForeignKey('asset.id'))
    target_asset_id = db.Column(db.BigInteger, db.ForeignKey('asset.id'))
    target_asset = db.relationship('Asset', uselist=False,
                                   foreign_keys=[target_asset_id])
    evaluated_at = db.Column(db.DateTime(timezone=False))
    granularity = db.Column(db.Enum('1sec', '1min', '5min', '1hour', '1day',
                                    '1week', '1month', name='granularity'))
    open = db.Column(db.Numeric(precision=20, scale=4))
    close = db.Column(db.Numeric(precision=20, scale=4))
    low = db.Column(db.Numeric(precision=20, scale=4))
    high = db.Column(db.Numeric(precision=20, scale=4))


class Asset(db.Model, CRUDMixin):
    name = db.Column(db.String)
    description = db.Column(db.Text)
    type = db.Column(db.Enum('currency', 'stock', 'bond', 'security', 'fund',
                             'commodity', name='asset_type'))
    # unit_price = db.Column(db.Numeric(precision=20, scale=4))

    #: Arbitrary data
    data = db.Column(JsonType)

    asset_values = db.relationship('AssetValue', backref='asset',
                                   foreign_keys=[AssetValue.asset_id],
                                   lazy='dynamic')

    def __repr__(self):
        return 'Asset <{} ({})>'.format(self.name, self.description)

    @property
    def unit_price(self):
        raise NotImplementedError

    @property
    def current_value(self):
        raise NotImplementedError


class Account(db.Model, CRUDMixin):
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.id'))
    type = db.Column(db.Enum('checking', 'savings', 'investment',
                             'credit_card', 'virtual', name='account_type'))
    name = db.Column(db.String)
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

    @property
    def balance(self):
        # Sum all transactions to produce {asset: sum(quantity)} dictionary
        bs = {}
        rs = [(r.asset, r.quantity) for r in self.records]
        for asset, quantity in rs:
            bs.setdefault(asset, 0)
            bs[asset] += quantity
        return bs

    def net_worth(self, evaluated_at=None):
        if not evaluated_at:
            evaluated_at = datetime.utcnow()

        nw = {}
        for asset, quantity in self.balance.items():
            asset_value = AssetValue.query \
                .filter(AssetValue.asset == asset,
                        AssetValue.evaluated_at == evaluated_at) \
                .first()
            worth = asset_value.close * quantity
            nw[asset] = worth

        return nw


class Transaction(db.Model, CRUDMixin):
    """A transaction consists of multiple records."""
    initiated_at = db.Column(db.DateTime(timezone=False))
    closed_at = db.Column(db.DateTime(timezone=False))
    state = db.Column(db.Enum('initiated', 'closed', 'pending', 'invalid',
                              name='transaction_state'))
    #: Individual record
    records = db.relationship('Record', backref='transaction',
                              lazy='dynamic')

    def __init__(self, initiated_at=None, *args, **kwargs):
        if initiated_at:
            self.initiated_at = initiated_at
        else:
            self.initiated_at = datetime.utcnow()
        self.state = 'initiated'
        super(self.__class__, self).__init__(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        """Implicitly mark the transaction as closed only if the state is
        'initiated'."""
        if self.state == 'initiated':
            self.close()

    def close(self, closed_at=None, commit=True):
        """Explicitly close a transaction."""
        if closed_at:
            self.closed_at = closed_at
        else:
            self.closed_at = datetime.utcnow()
        self.state = 'closed'

        if commit:
            db.session.commit()


class Record(db.Model, CRUDMixin):
    account_id = db.Column(db.BigInteger, db.ForeignKey('account.id'))
    transaction_id = db.Column(db.BigInteger, db.ForeignKey('transaction.id'))
    # NOTE: We'll always use the UTC time
    created_at = db.Column(db.DateTime(timezone=False))
    category = db.Column(db.String)
    asset_id = db.Column(db.BigInteger, db.ForeignKey('asset.id'))
    asset = db.relationship(Asset, uselist=False)
    quantity = db.Column(db.Numeric(precision=20, scale=4))
