"""add email record idempotency constraint

Revision ID: f1b9fcd21b7f
Revises: 9d8f3b71c2aa
Create Date: 2026-04-23 18:45:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f1b9fcd21b7f"
down_revision: Union[str, None] = "9d8f3b71c2aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_email_records_account_provider_message",
        "email_records",
        ["account_id", "provider_message_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_email_records_account_provider_message",
        "email_records",
        type_="unique",
    )
