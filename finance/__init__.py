import os
import sys

from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_cors import CORS
from flask_login import current_user, LoginManager
from logbook import Logger, StreamHandler


__version__ = '0.4.1'
__author__ = 'Sumin Byeon'
__email__ = 'suminb@gmail.com'


# FIXME: This is temporaroy
ADMINS = ['suminb@gmail.com']

StreamHandler(sys.stderr).push_application()
log = Logger('finance')


class AdminModelView(ModelView):
    def is_accessible(self):
        return not current_user.is_anonymous and \
            current_user.email in ADMINS


def create_app(name=__name__, config=None,
               static_folder='assets', template_folder='templates'):

    if config is None:
        config = {}

    app = Flask(name, static_folder=static_folder,
                template_folder=template_folder)
    app.secret_key = os.environ.get('SECRET', 'secret')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DEBUG'] = bool(os.environ.get('DEBUG', False))

    app.config.update(config)

    CORS(app, resources={r"/entities/*": {"origins": "*"}})

    from finance.models import db
    db.init_app(app)

    from finance.main import main_module
    app.register_blueprint(main_module, url_prefix='')

    admin = Admin(app, name='finance', template_mode='bootstrap3')
    from finance.models import (
        Account, Asset, AssetValue, Portfolio, Record, Transaction, User)
    classes = [Account, Asset, AssetValue, Portfolio, Record, Transaction,
               User]
    for cls in classes:
        admin.add_view(ModelView(cls, db.session,
                                 endpoint=cls.__name__))

    login_manager = LoginManager(app)
    login_manager.login_view = 'user.login'

    from finance.utils import date_range
    app.jinja_env.filters['date_range'] = date_range

    return app
