"""Make Asset.code unique

Revision ID: 3127ef2df8ce
Revises: 52e1b7734f7f
Create Date: 2018-03-26 23:49:26.781297

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "3127ef2df8ce"
down_revision = "52e1b7734f7f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint("unique_asset_code", "asset", ["code"])


def downgrade():
    op.drop_constraint("unique_asset_code", "asset", type_="unique")
