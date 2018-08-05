"""Initial state

Revision ID: 34a1efbca5fa
Revises:
Create Date: 2018-01-13 01:18:55.838885

"""
from alembic import op
import sqlalchemy as sa

from finance.models import JsonType


# revision identifiers, used by Alembic.
revision = '34a1efbca5fa'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'asset',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('type', sa.Enum(
            'currency', 'stock', 'bond', 'p2p_bond', 'security', 'fund',
            'commodity', name='asset_type'), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('code', sa.String(), nullable=True),
        sa.Column('isin', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('data', JsonType, nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'dart_report',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('registered_at', sa.DateTime(), nullable=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('entity', sa.String(), nullable=True),
        sa.Column('reporter', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'transaction',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('initiated_at', sa.DateTime(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('state', sa.Enum(
            'initiated', 'closed', 'pending', 'invalid',
            name='transaction_state'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'user',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('given_name', sa.String(), nullable=True),
        sa.Column('family_name', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('data', JsonType, nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_table(
        'asset_value',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('asset_id', sa.BigInteger(), nullable=True),
        sa.Column('base_asset_id', sa.BigInteger(), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(), nullable=True),
        sa.Column('granularity', sa.Enum(
            '1sec', '1min', '5min', '1hour', '1day', '1week', '1month',
            '1year', name='granularity'), nullable=True),
        sa.Column('open', sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column('high', sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column('low', sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column('close', sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column('volume', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['asset.id'], ),
        sa.ForeignKeyConstraint(['base_asset_id'], ['asset.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id', 'evaluated_at', 'granularity')
    )
    op.create_table(
        'portfolio',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('base_asset_id', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['base_asset_id'], ['asset.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'account',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('portfolio_id', sa.BigInteger(), nullable=True),
        sa.Column('type', sa.Enum(
            'checking', 'savings', 'investment', 'credit_card', 'virtual',
            name='account_type'), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('number', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('data', JsonType, nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolio.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'record',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('account_id', sa.BigInteger(), nullable=True),
        sa.Column('asset_id', sa.BigInteger(), nullable=True),
        sa.Column('transaction_id', sa.BigInteger(), nullable=True),
        sa.Column('type', sa.Enum(
            'deposit', 'withdraw', 'balance_adjustment', name='record_type'),
            nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('quantity',
                  sa.Numeric(precision=20, scale=4), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['account.id'], ),
        sa.ForeignKeyConstraint(['asset_id'], ['asset.id'], ),
        sa.ForeignKeyConstraint(['transaction_id'], ['transaction.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_id', 'asset_id', 'created_at', 'quantity')
    )


def downgrade():
    table_names = ('record', 'account', 'portfolio', 'asset_value', 'user',
                   'transaction', 'dart_report', 'asset')
    for table_name in table_names:
        op.drop_table(table_name)

    type_names = ('account_type', 'asset_type', 'granularity', 'record_type',
                  'transaction_state')
    for type_name in type_names:
        op.execute('DROP TYPE {0}'.format(type_name))
