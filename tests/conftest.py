import pytest

from finance import create_app
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
