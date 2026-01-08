"""Recreate Gift Asset tables with correct structure

Revision ID: 20241218_giftasset
Revises: fffe5004a96d
Create Date: 2024-12-18 17:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '20241218_giftasset'
down_revision = 'fffe5004a96d'
branch_labels = None
depends_on = None


def upgrade():
    # Удаляем все старые таблицы если они существуют
    op.execute("DROP TABLE IF EXISTS giftasset_update_stats CASCADE")
    op.execute("DROP TABLE IF EXISTS giftasset_metadata CASCADE")
    op.execute("DROP TABLE IF EXISTS giftasset_sales_history CASCADE")
    op.execute("DROP TABLE IF EXISTS giftasset_provider_stats CASCADE")
    op.execute("DROP TABLE IF EXISTS giftasset_price_history CASCADE")
    op.execute("DROP TABLE IF EXISTS giftasset_market_cap CASCADE")
    op.execute("DROP TABLE IF EXISTS giftasset_health_index CASCADE")
    op.execute("DROP TABLE IF EXISTS giftasset_emission CASCADE")
    op.execute("DROP TABLE IF EXISTS giftasset_volumes CASCADE")
    op.execute("DROP TABLE IF EXISTS giftasset_price_list CASCADE")
    
    # 1. giftasset_price_list
    op.create_table(
        'giftasset_price_list',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('collection_name', sa.String(length=255), nullable=False),
        sa.Column('model_name', sa.String(length=255), nullable=True),
        sa.Column('price_getgems', sa.Float(), nullable=True),
        sa.Column('price_mrkt', sa.Float(), nullable=True),
        sa.Column('price_portals', sa.Float(), nullable=True),
        sa.Column('price_tonnel', sa.Float(), nullable=True),
        sa.Column('last_update', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('collection_name', 'model_name', name='giftasset_price_list_collection_model_key')
    )
    op.create_index('idx_giftasset_price_collection_model', 'giftasset_price_list', ['collection_name', 'model_name'])
    op.create_index(op.f('ix_giftasset_price_list_collection_name'), 'giftasset_price_list', ['collection_name'])
    op.create_index(op.f('ix_giftasset_price_list_model_name'), 'giftasset_price_list', ['model_name'])
    
    # 2. giftasset_volumes
    op.create_table(
        'giftasset_volumes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('collection_name', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('hour_revenue', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('hour_sales', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_revenue', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_sales', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('peak_hour', sa.DateTime(), nullable=True),
        sa.Column('peak_hour_revenue_percent', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('peak_hour_sales_percent', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('sales_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('collection_name', 'provider', 'sales_date', name='giftasset_volumes_collection_provider_date_key')
    )
    op.create_index('idx_giftasset_volume_collection_provider_date', 'giftasset_volumes', ['collection_name', 'provider', 'sales_date'])
    op.create_index(op.f('ix_giftasset_volumes_collection_name'), 'giftasset_volumes', ['collection_name'])
    op.create_index(op.f('ix_giftasset_volumes_provider'), 'giftasset_volumes', ['provider'])
    op.create_index(op.f('ix_giftasset_volumes_sales_date'), 'giftasset_volumes', ['sales_date'])
    
    # 3. giftasset_emission
    op.create_table(
        'giftasset_emission',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('collection_name', sa.String(length=255), nullable=False),
        sa.Column('emission', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('deleted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('hidden', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('refunded', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('upgraded', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unique_owners', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('top_30_whales_hold', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('mrkt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('portals_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tonnel_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('mrkt_percentage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('portals_percentage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('tonnel_percentage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('collection_name', name='giftasset_emission_collection_name_key')
    )
    op.create_index(op.f('ix_giftasset_emission_collection_name'), 'giftasset_emission', ['collection_name'], unique=True)
    
    # 4. giftasset_health_index
    op.create_table(
        'giftasset_health_index',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('collection_name', sa.String(length=255), nullable=False),
        sa.Column('health_index', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('liquidity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('market_cap', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('whale_concentration', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('norm_liquidity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('norm_market_cap', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('norm_whale_concentration', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('collection_name', name='giftasset_health_index_collection_name_key')
    )
    op.create_index(op.f('ix_giftasset_health_index_collection_name'), 'giftasset_health_index', ['collection_name'], unique=True)
    
    # 5. giftasset_market_cap
    op.create_table(
        'giftasset_market_cap',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('total_market_cap', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('collections_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('record_date', sa.Date(), nullable=False),
        sa.Column('record_datetime', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_giftasset_market_cap_record_date'), 'giftasset_market_cap', ['record_date'])
    op.create_index(op.f('ix_giftasset_market_cap_record_datetime'), 'giftasset_market_cap', ['record_datetime'])
    
    # 6. giftasset_price_history
    op.create_table(
        'giftasset_price_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('collection_name', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('period_type', sa.String(length=10), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('price_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_giftasset_price_history_collection_provider_date', 'giftasset_price_history', ['collection_name', 'provider', 'price_date'])
    op.create_index(op.f('ix_giftasset_price_history_collection_name'), 'giftasset_price_history', ['collection_name'])
    op.create_index(op.f('ix_giftasset_price_history_period_type'), 'giftasset_price_history', ['period_type'])
    op.create_index(op.f('ix_giftasset_price_history_price_date'), 'giftasset_price_history', ['price_date'])
    op.create_index(op.f('ix_giftasset_price_history_provider'), 'giftasset_price_history', ['provider'])
    
    # 7. giftasset_provider_stats
    op.create_table(
        'giftasset_provider_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('hour_revenue', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('hour_sales', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_revenue', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_sales', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('peak_hour', sa.String(length=50), nullable=True),
        sa.Column('peak_hour_revenue_percent', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('peak_hour_sales_percent', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('fee', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', name='giftasset_provider_stats_provider_key')
    )
    op.create_index(op.f('ix_giftasset_provider_stats_provider'), 'giftasset_provider_stats', ['provider'], unique=True)
    
    # 8. giftasset_sales_history
    op.create_table(
        'giftasset_sales_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('collection_name', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('telegram_gift_id', sa.String(length=50), nullable=False),
        sa.Column('telegram_gift_name', sa.String(length=255), nullable=False),
        sa.Column('telegram_gift_number', sa.Integer(), nullable=False),
        sa.Column('unix_time', sa.Integer(), nullable=False),
        sa.Column('sale_datetime', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_gift_id', 'unix_time', name='giftasset_sales_history_telegram_gift_id_unix_time_key')
    )
    op.create_index('idx_giftasset_sales_collection_provider_time', 'giftasset_sales_history', ['collection_name', 'provider', 'sale_datetime'])
    op.create_index(op.f('ix_giftasset_sales_history_collection_name'), 'giftasset_sales_history', ['collection_name'])
    op.create_index(op.f('ix_giftasset_sales_history_provider'), 'giftasset_sales_history', ['provider'])
    op.create_index(op.f('ix_giftasset_sales_history_sale_datetime'), 'giftasset_sales_history', ['sale_datetime'])
    op.create_index(op.f('ix_giftasset_sales_history_telegram_gift_id'), 'giftasset_sales_history', ['telegram_gift_id'])
    op.create_index(op.f('ix_giftasset_sales_history_unix_time'), 'giftasset_sales_history', ['unix_time'])
    
    # 9. giftasset_metadata
    op.create_table(
        'giftasset_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('collection_name', sa.String(length=255), nullable=False),
        sa.Column('telegram_id', sa.String(length=50), nullable=True),
        sa.Column('backdrops', JSONB, nullable=True),
        sa.Column('patterns', JSONB, nullable=True),
        sa.Column('models', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('collection_name', name='giftasset_metadata_collection_name_key')
    )
    op.create_index(op.f('ix_giftasset_metadata_collection_name'), 'giftasset_metadata', ['collection_name'], unique=True)
    op.create_index(op.f('ix_giftasset_metadata_telegram_id'), 'giftasset_metadata', ['telegram_id'])
    
    # 10. giftasset_update_stats
    op.create_table(
        'giftasset_update_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('endpoint', sa.String(length=255), nullable=False),
        sa.Column('last_update', sa.DateTime(), nullable=False),
        sa.Column('update_frequency_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='success'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_giftasset_update_stats_endpoint'), 'giftasset_update_stats', ['endpoint'], unique=True)


def downgrade():
    op.drop_table('giftasset_update_stats')
    op.drop_table('giftasset_metadata')
    op.drop_table('giftasset_sales_history')
    op.drop_table('giftasset_provider_stats')
    op.drop_table('giftasset_price_history')
    op.drop_table('giftasset_market_cap')
    op.drop_table('giftasset_health_index')
    op.drop_table('giftasset_emission')
    op.drop_table('giftasset_volumes')
    op.drop_table('giftasset_price_list')
