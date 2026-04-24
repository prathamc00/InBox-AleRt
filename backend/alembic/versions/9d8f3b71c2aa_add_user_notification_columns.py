"""add user notification columns

Revision ID: 9d8f3b71c2aa
Revises: 76ef619cf6c0
Create Date: 2026-04-23 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9d8f3b71c2aa"
down_revision: Union[str, None] = "76ef619cf6c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "notify_on_all",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "notify_daily_digest",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    op.alter_column("users", "notify_on_all", server_default=None)
    op.alter_column("users", "notify_daily_digest", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "notify_daily_digest")
    op.drop_column("users", "notify_on_all")
