"""Alter granularity and asset_value

Revision ID: ecaa0e473819
Revises: 8b831ca52f15
Create Date: 2021-05-01 18:46:18.455748

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ecaa0e473819'
down_revision = '8b831ca52f15'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("COMMIT")
    op.execute("ALTER TYPE granularity ADD VALUE '3min'")
    op.execute("ALTER TYPE granularity ADD VALUE '15min'")
    op.execute("ALTER TYPE granularity ADD VALUE '4hour'")
    op.execute("ALTER TYPE granularity RENAME TO ticker_granularity")

    op.execute("ALTER TYPE asset_value_source ADD VALUE 'upbit'")
    op.execute("ALTER TABLE asset_value ALTER COLUMN open TYPE numeric(18, 10)")
    op.execute("ALTER TABLE asset_value ALTER COLUMN close TYPE numeric(18, 10)")
    op.execute("ALTER TABLE asset_value ALTER COLUMN low TYPE numeric(18, 10)")
    op.execute("ALTER TABLE asset_value ALTER COLUMN high TYPE numeric(18, 10)")
    op.execute("ALTER TABLE asset_value ALTER COLUMN volume TYPE numeric(18, 10)")

    op.execute("ALTER TYPE asset_type RENAME VALUE 'currency' TO 'fiat_currency'")
    op.execute("ALTER TYPE asset_type ADD VALUE 'crypto_currency'")


def downgrade():
    """Fully functional downgrade is not supported. Shall be used in testing environments only."""
    raise RuntimeError("Downgrade is not supported")
    # op.execute("ALTER TABLE asset_value ALTER COLUMN granularity TYPE VARCHAR(255)")
    # op.execute("DROP TYPE ticker_granularity")
    # op.execute("CREATE TYPE granularity AS ENUM('1sec', '1min', '5min', '1hour', '1day', '1week', '1month', '1year')")
    # # NOTE: This will introduce errors if there is non-mappable values in asset_value.granularity.
    # op.execute("ALTER TABLE asset ALTER COLUMN granularity TYPE granularity USING granularity::granularity")

    # op.execute("ALTER TABLE asset_value ALTER COLUMN source TYPE VARCHAR(255)")
    # op.execute("DROP TYPE asset_value_source")
    # op.execute("CREATE TYPE asset_value_source AS ENUM('yahoo', 'google', 'kofia')")
    # # NOTE: This will introduce errors if there is non-mappable values in asset_value.source.
    # op.execute("ALTER TABLE asset ALTER COLUMN source TYPE source USING source::asset_value_source")
    #
    # op.execute("ALTER TABLE asset ALTER COLUMN type TYPE VARCHAR(255)")
    # op.execute("DROP TYPE asset_type")
    # op.execute("UPDATE asset SET type='currency' WHERE type='fiat_currency' OR type='crypto_currency'")
    # op.execute(
    #     "CREATE TYPE asset_type AS ENUM('currency', 'stock', 'bond', 'p2p_bond', 'security', 'fund', 'commodity')")
    # op.execute("ALTER TABLE asset ALTER COLUMN type TYPE asset_type USING type::asset_type")
