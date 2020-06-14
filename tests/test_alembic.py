from alembic import command
from alembic.config import Config
import pytest

from finance.models import Base


@pytest.fixture
def config():
    config = Config("alembic.ini")

    # NOTE: The following value will be evalutated in
    # alembic/env:run_migration_online()
    config.set_main_option("pytest.istest", "true")

    return config


@pytest.mark.skip
def test_upgrade(config, base_class, engine, session):
    # NOTE: At this point, all the tables should be populated by the `db`
    # fixture. So we drop all tables first.
    Base.metadata.drop_all(engine)
    session.execute("DROP TABLE IF EXISTS alembic_version")

    command.upgrade(config, "head")
    command.downgrade(config, "base")

    # Finally we need to drop `alembic_version`
    session.execute("DROP TABLE alembic_version")
