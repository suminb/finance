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


def downgrade():
    # NOTE: There is no way back...
    op.execute("ALTER TYPE ticker_granularity RENAME TO granularity")
