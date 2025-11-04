"""Drop dart_report table

Revision ID: 3cf537f1485a
Revises: ecaa0e473819
Create Date: 2025-11-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3cf537f1485a"
down_revision = "ecaa0e473819"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("dart_report")


def downgrade():
    op.create_table(
        "dart_report",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("registered_at", sa.DateTime(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("entity", sa.String(), nullable=True),
        sa.Column("reporter", sa.String(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

