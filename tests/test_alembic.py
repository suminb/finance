from alembic import command
from alembic.config import Config
import pytest


@pytest.fixture
def config():
    config = Config('alembic.ini')

    # NOTE: The following value will be evalutated in
    # alembic/env:run_migration_online()
    config.set_main_option('pytest.istest', 'true')

def test_headquarters_upgrade(config):
    command.upgrade(config, 'head')


def test_headquarters_downgrade(config):
    command.downgrade(config, 'base')
    command.upgrade(config, 'head')
