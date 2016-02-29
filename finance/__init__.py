import os
import sys

from flask import Flask
from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.login import current_user, LoginManager
from logbook import Logger, StreamHandler


# FIXME: This is temporaroy
ADMINS = ['suminb@gmail.com']

StreamHandler(sys.stdout).push_application()
log = Logger('finance')


class AdminModelView(ModelView):
    def is_accessible(self):
        return not current_user.is_anonymous and \
            current_user.email in ADMINS


def create_app(name=__name__, config={},
               static_folder='static', template_folder='templates'):

    app = Flask(name, static_folder=static_folder,
                template_folder=template_folder)
    app.secret_key = os.environ.get('SECRET', 'secret')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DB_URI']
    app.config['DEBUG'] = bool(os.environ.get('DEBUG', False))

    app.config.update(config)

    from finance.models import db
    db.init_app(app)

    from finance.main import main_module
    app.register_blueprint(main_module, url_prefix='')

    admin = Admin(app, name='finance', template_mode='bootstrap3')
    from finance.models import Account, Asset, Record, Transaction, User
    classes = [Account, Asset, Record, Transaction, User]
    for cls in classes:
        admin.add_view(ModelView(cls, db.session,
                                 endpoint=cls.__name__))

    login_manager = LoginManager(app)
    login_manager.login_view = 'user.login'

    return app
