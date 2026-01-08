"""Remove unique constraint from accounts.telegram_id

Revision ID: 20241209_001
Revises: ca884ab85b6f
Create Date: 2024-12-09

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '20241209_001'
down_revision = 'ca884ab85b6f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Удаляем уникальный индекс
    op.drop_index('ix_accounts_telegram_id', table_name='accounts')
    # Создаём обычный индекс (не уникальный)
    op.create_index('ix_accounts_telegram_id', 'accounts', ['telegram_id'], unique=False)


def downgrade() -> None:
    # Удаляем обычный индекс
    op.drop_index('ix_accounts_telegram_id', table_name='accounts')
    # Создаём уникальный индекс обратно
    op.create_index('ix_accounts_telegram_id', 'accounts', ['telegram_id'], unique=True)
