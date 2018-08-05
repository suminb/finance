"""Add 'test' enum field for AssetValue

Revision ID: 52e1b7734f7f
Revises: f9b65d2cf683
Create Date: 2018-03-14 00:13:44.054824

"""
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '52e1b7734f7f'
down_revision = 'f9b65d2cf683'
branch_labels = None
depends_on = None

new_type = postgresql.ENUM(
    'yahoo', 'google', 'kofia', 'test', name='asset_value_source')
old_type = postgresql.ENUM(
    'yahoo', 'google', 'kofia', name='asset_value_source')


def upgrade():
    op.alter_column(
        'asset_value', 'source', type_=new_type, existing_type=old_type,
        nullable=False)


def downgrade():
    op.alter_column(
        'asset_value', 'source', type_=old_type, existing_type=new_type,
        nullable=False)
