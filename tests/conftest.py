import pytest

from finance import create_app
from finance.models import Account, Asset
from finance.models import db as _db


@pytest.fixture(scope='session')
def app(request):
    """Session-wide test `Flask` application."""
    settings_override = {
        'TESTING': True,
    }
    app = create_app(__name__, config=settings_override)

    # Establish an application context before running the tests.
    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    return app


@pytest.fixture(scope='session')
def db(app, request):
    """Session-wide test database."""
    def teardown():
        # _db.drop_all()
        pass

    _db.app = app
    _db.create_all()

    request.addfinalizer(teardown)
    return _db


@pytest.fixture(scope='session')
def account_checking(request, db):
    def teardown():
        db.session.delete(account)
        db.session.commit()
    request.addfinalizer(teardown)
    account = Account.create(type='checking', name='Shinhan Checking')
    return account


@pytest.fixture(scope='session')
def account_sp500(request, db):
    def teardown():
        db.session.delete(account)
        db.session.commit()
    request.addfinalizer(teardown)
    account = Account.create(type='investment', name='S&P500 Fund')
    return account


@pytest.fixture(scope='session')
def asset_krw(request, db):
    def teardown():
        db.session.delete(asset)
        db.session.commit()
    request.addfinalizer(teardown)
    asset = Asset.create(
        type='currency', name='KRW', description='Korean Won')
    return asset


@pytest.fixture(scope='session')
def asset_sp500(request, db):
    def teardown():
        db.session.delete(asset)
        db.session.commit()
    request.addfinalizer(teardown)
    asset = Asset.create(
        type='security', name='S&P 500', description='')
    return asset
