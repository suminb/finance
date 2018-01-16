from alembic import command
from alembic.config import Config
import pytest


@pytest.fixture
def config():
    config = Config('alembic.ini')

    # NOTE: The following value will be evalutated in
    # alembic/env:run_migration_online()
    config.set_main_option('pytest.istest', 'true')

    return config


def test_upgrade(config, db):
    # NOTE: At this point, all the tables should be populated by the `db`
    # fixture. So we drop all tables first.
    db.drop_all()
    db.engine.execute('DROP TABLE IF EXISTS alembic_version')

    command.upgrade(config, 'head')
    command.downgrade(config, 'base')

    # Finally we need to drop `alembic_version`
    db.engine.execute('DROP TABLE alembic_version')
