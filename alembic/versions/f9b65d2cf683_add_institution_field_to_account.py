"""Add institution field to Account

Revision ID: f9b65d2cf683
Revises: 1bac2db8d359
Create Date: 2018-03-08 00:05:47.475245

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f9b65d2cf683'
down_revision = '1bac2db8d359'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'account', sa.Column('institution', sa.String(), nullable=True))
    op.create_unique_constraint(
        'account_institution_number_key', 'account', ['institution', 'number'])


def downgrade():
    op.drop_constraint(
        'account_institution_number_key', 'account', type_='unique')
    op.drop_column('account', 'institution')
