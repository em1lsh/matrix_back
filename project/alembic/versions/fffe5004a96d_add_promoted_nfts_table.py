"""add_promoted_nfts_table

Revision ID: fffe5004a96d
Revises: 20241216_add_stars_purchases
Create Date: 2025-12-16 21:56:04.230063

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fffe5004a96d'
down_revision = '20241216_add_stars_purchases'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создание таблицы promoted_nfts
    op.create_table(
        'promoted_nfts',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('nft_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('ends_at', sa.DateTime(), nullable=False),
        sa.Column('total_costs', sa.BigInteger(), nullable=False, comment='Общая стоимость продвижения в nanotons'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['nft_id'], ['nfts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Создание индексов
    op.create_index('ix_promoted_nfts_nft_active', 'promoted_nfts', ['nft_id', 'is_active'])
    op.create_index('ix_promoted_nfts_user_active', 'promoted_nfts', ['user_id', 'is_active'])
    op.create_index('ix_promoted_nfts_ends_at', 'promoted_nfts', ['ends_at'])
    op.create_index('ix_promoted_nfts_active', 'promoted_nfts', ['is_active'])
    
    # Уникальный индекс для активных продвижений (только одно активное продвижение на NFT)
    op.create_index(
        'ix_promoted_nfts_unique_active', 
        'promoted_nfts', 
        ['nft_id'], 
        unique=True,
        postgresql_where=sa.text('is_active = true')
    )


def downgrade() -> None:
    # Удаление индексов
    op.drop_index('ix_promoted_nfts_unique_active', 'promoted_nfts')
    op.drop_index('ix_promoted_nfts_active', 'promoted_nfts')
    op.drop_index('ix_promoted_nfts_ends_at', 'promoted_nfts')
    op.drop_index('ix_promoted_nfts_user_active', 'promoted_nfts')
    op.drop_index('ix_promoted_nfts_nft_active', 'promoted_nfts')
    
    # Удаление таблицы
    op.drop_table('promoted_nfts') 