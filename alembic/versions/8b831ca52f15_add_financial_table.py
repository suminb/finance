"""Add financial table

Revision ID: 8b831ca52f15
Revises: 3127ef2df8ce
Create Date: 2021-01-15 02:17:04.860188

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8b831ca52f15"
down_revision = "3127ef2df8ce"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column(
            "granularity",
            # NOTE: 'quarterly' can be both an adjective and an adverb.
            sa.Enum("quarterly", "annual", name="financial_granularity"),
            nullable=False,
        ),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.SmallInteger(), nullable=False),
        sa.Column("value", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "key", "granularity", "year", "quarter"),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["asset.id"],
        ),
    )


def downgrade():
    op.drop_table("financial")
    op.execute("DROP TYPE financial_granularity")
