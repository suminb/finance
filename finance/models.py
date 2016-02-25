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

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=False)

    def __init__(self, *args, **kwargs):
        self.id = uuid64.issue()

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


class Asset(CRUDMixin, db.Model):
    name = db.Column(db.String)
    description = db.Column(db.Text)
    unit_price = db.Column(db.Numeric(precision=20, scale=4))

    #: Arbitrary data
    data = db.Column(JsonType)

    def __repr__(self):
        return 'Asset <{} ({})>'.format(self.name, self.description)

    @property
    def unit_price(self):
        raise NotImplementedError


class Account(CRUDMixin, db.Model):
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.id'))
    type = db.Column(db.Enum('checking', 'savings', 'loan', 'bond', 'stock',
                             name='account_type'))
    name = db.Column(db.String)
    description = db.Column(db.Text)

    #: Arbitrary data
    data = db.Column(JsonType)

    transactions = db.relationship('Transaction', backref='account',
                                   lazy='dynamic')

    def __repr__(self):
        return 'Account <{} ({})>'.format(self.name, self.type)

    @property
    def balance(self):
        raise NotImplementedError


class Transaction(CRUDMixin, db.Model):
    account_id = db.Column(db.BigInteger, db.ForeignKey('account.id'))
    # NOTE: We'll always use the UTC time
    initiated_at = db.Column(db.DateTime(timezone=False))
    closed_at = db.Column(db.DateTime(timezone=False))
    state = db.Column(db.Enum('open', 'closed', 'pending', 'invalid',
                              name='transaction_state'))
    category = db.Column(db.String)
    asset_id = db.Column(db.BigInteger, db.ForeignKey('asset.id'))
    asset = db.relationship(Asset, uselist=False)
    quantity = db.Column(db.BigInteger)
