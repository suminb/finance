from finance import create_app
from finance.models import *  # noqa


def test_transaction():
    app = create_app(__name__)
    with app.app_context():
        with Transaction.create() as t:
            t.state = 'xxxx'
