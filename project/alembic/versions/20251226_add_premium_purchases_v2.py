"""Add premium_purchases table with user_id and price_nanotons

Revision ID: 20251226_premium_v2
Revises: 20241218_giftasset
Create Date: 2025-12-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251226_premium_v2'
down_revision = '20241218_giftasset'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'premium_purchases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('recipient_username', sa.String(255), nullable=False),
        sa.Column('months', sa.Integer(), nullable=False, comment='Месяцев подписки (3, 6, 12)'),
        sa.Column('show_sender', sa.Boolean(), default=False),
        sa.Column('price_nanotons', sa.BigInteger(), nullable=False, comment='Цена в nanotons'),
        sa.Column('ton_price', sa.String(50), nullable=True, comment='Цена в TON от Fragment'),
        sa.Column('fragment_tx_id', sa.String(255), nullable=True, comment='UUID транзакции'),
        sa.Column('ref_id', sa.String(255), nullable=True, comment='Reference ID'),
        sa.Column('status', sa.String(32), default='pending'),
        sa.Column('error_message', sa.String(500), nullable=True),
        sa.Column('fragment_response', sa.String(2000), nullable=True, comment='JSON ответ Fragment'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    
    op.create_index('ix_premium_purchases_user_id', 'premium_purchases', ['user_id'])
    op.create_index('ix_premium_purchases_user_created', 'premium_purchases', ['user_id', 'created_at'])
    op.create_index('ix_premium_purchases_status', 'premium_purchases', ['status'])
    op.create_index('ix_premium_purchases_recipient', 'premium_purchases', ['recipient_username'])
    op.create_index('ix_premium_purchases_fragment_tx_id', 'premium_purchases', ['fragment_tx_id'])


def downgrade() -> None:
    op.drop_index('ix_premium_purchases_fragment_tx_id', table_name='premium_purchases')
    op.drop_index('ix_premium_purchases_recipient', table_name='premium_purchases')
    op.drop_index('ix_premium_purchases_status', table_name='premium_purchases')
    op.drop_index('ix_premium_purchases_user_created', table_name='premium_purchases')
    op.drop_index('ix_premium_purchases_user_id', table_name='premium_purchases')
    op.drop_table('premium_purchases')
