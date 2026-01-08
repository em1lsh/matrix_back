"""merge_bundles_and_buy_orders

Revision ID: ff81c827f56c
Revises: 20251227_bundle_offers, buy_orders_module
Create Date: 2025-12-29 00:16:33.915599

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ff81c827f56c'
down_revision = ('20251227_bundle_offers', 'buy_orders_module')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass 