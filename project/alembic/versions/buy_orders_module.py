"""Add buy orders tables.

Revision ID: buy_orders_module
Revises: 20251226_premium_v2
Create Date: 2025-02-20

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "buy_orders_module"
down_revision = "20251226_premium_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "buy_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("buyer_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("pattern_name", sa.String(length=255), nullable=True),
        sa.Column("backdrop_name", sa.String(length=255), nullable=True),
        sa.Column("price_limit", sa.BigInteger(), nullable=False),
        sa.Column("quantity_total", sa.Integer(), nullable=False),
        sa.Column("quantity_remaining", sa.Integer(), nullable=False),
        sa.Column("frozen_amount", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("quantity_total > 0", name="check_buy_order_quantity_positive"),
        sa.CheckConstraint("quantity_remaining >= 0", name="check_buy_order_quantity_remaining_non_negative"),
        sa.CheckConstraint("price_limit > 0", name="check_buy_order_price_positive"),
        sa.CheckConstraint("frozen_amount >= 0", name="check_buy_order_frozen_amount_non_negative"),
    )

    op.create_index("ix_buy_orders_buyer_id", "buy_orders", ["buyer_id"])
    op.create_index("ix_buy_orders_title", "buy_orders", ["title"])
    op.create_index("ix_buy_orders_model_name", "buy_orders", ["model_name"])
    op.create_index("ix_buy_orders_pattern_name", "buy_orders", ["pattern_name"])
    op.create_index("ix_buy_orders_backdrop_name", "buy_orders", ["backdrop_name"])
    op.create_index("ix_buy_orders_price_limit", "buy_orders", ["price_limit"])
    op.create_index("ix_buy_orders_quantity_remaining", "buy_orders", ["quantity_remaining"])
    op.create_index("ix_buy_orders_status", "buy_orders", ["status"])

    op.create_index(
        "ix_buy_orders_title_model_pattern_backdrop",
        "buy_orders",
        ["title", "model_name", "pattern_name", "backdrop_name"],
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX ix_buy_orders_title_status_price_created "
            "ON buy_orders (title, status, price_limit DESC, created_at ASC)"
        )
    else:
        op.create_index(
            "ix_buy_orders_title_status_price_created",
            "buy_orders",
            ["title", "status", "price_limit", "created_at"],
        )

    op.create_table(
        "buy_order_deals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.BigInteger(), sa.ForeignKey("buy_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nft_id", sa.BigInteger(), sa.ForeignKey("nfts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("gift_id", sa.BigInteger(), sa.ForeignKey("gifts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("buyer_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("seller_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reserved_unit_price", sa.BigInteger(), nullable=False),
        sa.Column("execution_price", sa.BigInteger(), nullable=False),
        sa.Column("commission", sa.BigInteger(), nullable=False),
        sa.Column("seller_amount", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("nft_deal_id", sa.BigInteger(), sa.ForeignKey("nft_deals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index("ix_buy_order_deals_order_nft", "buy_order_deals", ["order_id", "nft_id"])
    op.create_index("ix_buy_order_deals_buyer_seller", "buy_order_deals", ["buyer_id", "seller_id"])
    op.create_index("ix_buy_order_deals_order_id", "buy_order_deals", ["order_id"])
    op.create_index("ix_buy_order_deals_nft_id", "buy_order_deals", ["nft_id"])
    op.create_index("ix_buy_order_deals_gift_id", "buy_order_deals", ["gift_id"])
    op.create_index("ix_buy_order_deals_buyer_id", "buy_order_deals", ["buyer_id"])
    op.create_index("ix_buy_order_deals_seller_id", "buy_order_deals", ["seller_id"])


def downgrade() -> None:
    op.drop_table("buy_order_deals")
    op.drop_table("buy_orders")