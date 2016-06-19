from functools import partial
import os

import pytest
from typedecorator import setup_typecheck

from finance import create_app
from finance.models import Account, Asset, Portfolio
from finance.models import db as _db


setup_typecheck()


@pytest.fixture(scope='module')
def app(request):
    """Session-wide test `Flask` application."""
    settings_override = {
        'TESTING': True,
    }
    if 'TEST_DB_URI' in os.environ:
        settings_override['SQLALCHEMY_DATABASE_URI'] = \
            os.environ.get('TEST_DB_URI')
    app = create_app(__name__, config=settings_override)

    # Establish an application context before running the tests.
    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    return app


@pytest.fixture
def testapp(app, db):
    return app.test_client()


@pytest.fixture(scope='module')
def db(app, request):
    """Session-wide test database."""
    def teardown():
        _db.drop_all()

    _db.app = app
    _db.create_all()

    request.addfinalizer(teardown)
    return _db


@pytest.fixture(scope='function')
def account_checking(request, db):
    account = Account.create(type='checking', name='신한은행 입출금')
    request.addfinalizer(partial(teardown, db=db, record=account))
    return account


@pytest.fixture(scope='function')
def account_savings(request, db):
    account = Account.create(type='savings', name='신한은행 적금')
    request.addfinalizer(partial(teardown, db=db, record=account))
    return account


@pytest.fixture(scope='function')
def account_hf(request, db):
    account = Account.create(type='virtual', name='어니스트펀드')
    request.addfinalizer(partial(teardown, db=db, record=account))
    return account


@pytest.fixture(scope='function')
def account_sp500(request, db):
    account = Account.create(type='investment', name='S&P500 Fund')
    request.addfinalizer(partial(teardown, db=db, record=account))
    return account


@pytest.fixture(scope='module')
def asset_hf1(request, db):
    asset = Asset.create(
        type='bond', name='포트폴리오 투자상품 1호')
    request.addfinalizer(partial(teardown, db=db, record=asset))
    return asset


@pytest.fixture(scope='module')
def asset_krw(request, db):
    asset = Asset.create(
        type='currency', name='KRW', description='Korean Won')
    request.addfinalizer(partial(teardown, db=db, record=asset))
    return asset


@pytest.fixture(scope='module')
def asset_sp500(request, db):
    asset = Asset.create(
        type='security', name='KB Star S&P500', description='',
        data={'code': 'KR5223941018'})
    request.addfinalizer(partial(teardown, db=db, record=asset))
    return asset


@pytest.fixture(scope='module')
def asset_usd(request, db):
    asset = Asset.create(
        type='currency', name='USD', description='United States Dollar')
    request.addfinalizer(partial(teardown, db=db, record=asset))
    return asset


@pytest.fixture(scope='function')
def portfolio(request, db, asset_krw, account_checking, account_sp500):
    p = Portfolio.create(base_asset=asset_krw)
    p.add_accounts(account_checking, account_sp500)

    def teardown():
        # NOTE: The following statement is necessary because the scope of
        # `asset_krw` is a module, whereas the scope of `p` is a function.
        p.base_asset = None
        db.session.delete(p)
        db.session.commit()

    request.addfinalizer(teardown)
    return p


def teardown(db, record):
    db.session.delete(record)
    db.session.commit()
