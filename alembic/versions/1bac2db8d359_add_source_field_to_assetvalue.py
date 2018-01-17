"""Add source field to AssetValue

Revision ID: 1bac2db8d359
Revises: 34a1efbca5fa
Create Date: 2018-01-18 01:07:18.886601

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


# revision identifiers, used by Alembic.
revision = '1bac2db8d359'
down_revision = '34a1efbca5fa'
branch_labels = None
depends_on = None


def upgrade():
    # If we don't do this, Alembic won't create the type automatically
    enum_type = ENUM('yahoo', 'google', name='asset_value_source')
    enum_type.create(op.get_bind())

    op.add_column(
        'asset_value',
        sa.Column('source', enum_type, nullable=False))


def downgrade():
    op.drop_column('asset_value', 'source')
