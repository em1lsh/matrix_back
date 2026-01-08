"""Add frozen_balance to users table

Revision ID: 20241211_frozen
Revises: 20241209_remove_unique_telegram_id
Create Date: 2024-12-11

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20241211_frozen"
down_revision = "20241209_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "frozen_balance",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
            comment="Замороженный баланс (в nanotons) - средства в активных офферах",
        ),
    )
    # Добавляем индекс для быстрого поиска пользователей с замороженными средствами
    op.create_index("ix_users_frozen_balance", "users", ["frozen_balance"], postgresql_where=sa.text("frozen_balance > 0"))


def downgrade() -> None:
    op.drop_index("ix_users_frozen_balance", table_name="users")
    op.drop_column("users", "frozen_balance")
