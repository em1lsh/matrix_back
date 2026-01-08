"""Add NFT bundles and order event logs

Revision ID: 20251227_bundles
Revises: 20251226_premium_v2
Create Date: 2025-12-27

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20251227_bundles"
down_revision = "20251226_premium_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nft_bundles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("seller_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price_nanotons", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nft_bundles_status", "nft_bundles", ["status"])
    op.create_index("ix_nft_bundles_seller_status", "nft_bundles", ["seller_id", "status"])
    op.create_index("ix_nft_bundles_created_at", "nft_bundles", ["created_at"])
    op.create_index("ix_nft_bundles_price_nanotons", "nft_bundles", ["price_nanotons"])

    op.create_table(
        "nft_bundle_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bundle_id", sa.Integer(), sa.ForeignKey("nft_bundles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nft_id", sa.Integer(), sa.ForeignKey("nfts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bundle_id", "nft_id", name="uq_nft_bundle_items_bundle_nft"),
    )
    op.create_index("ix_nft_bundle_items_nft_id", "nft_bundle_items", ["nft_id"])
    op.create_index("ix_nft_bundle_items_bundle_id", "nft_bundle_items", ["bundle_id"])

    op.add_column(
        "nfts",
        sa.Column("active_bundle_id", sa.Integer(), sa.ForeignKey("nft_bundles.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_nfts_active_bundle_id", "nfts", ["active_bundle_id"])

    op.create_table(
        "nft_order_event_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("offer_id", sa.Integer(), sa.ForeignKey("nft_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("nft_id", sa.Integer(), sa.ForeignKey("nfts.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "actor_user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "counterparty_user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("amount_nanotons", sa.BigInteger(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nft_order_event_logs_offer_id", "nft_order_event_logs", ["offer_id"])
    op.create_index("ix_nft_order_event_logs_nft_id", "nft_order_event_logs", ["nft_id"])
    op.create_index("ix_nft_order_event_logs_event_type", "nft_order_event_logs", ["event_type"])
    op.create_index("ix_nft_order_event_logs_created_at", "nft_order_event_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_nft_order_event_logs_created_at", table_name="nft_order_event_logs")
    op.drop_index("ix_nft_order_event_logs_event_type", table_name="nft_order_event_logs")
    op.drop_index("ix_nft_order_event_logs_nft_id", table_name="nft_order_event_logs")
    op.drop_index("ix_nft_order_event_logs_offer_id", table_name="nft_order_event_logs")
    op.drop_table("nft_order_event_logs")

    op.drop_index("ix_nfts_active_bundle_id", table_name="nfts")
    op.drop_column("nfts", "active_bundle_id")

    op.drop_index("ix_nft_bundle_items_bundle_id", table_name="nft_bundle_items")
    op.drop_index("ix_nft_bundle_items_nft_id", table_name="nft_bundle_items")
    op.drop_table("nft_bundle_items")

    op.drop_index("ix_nft_bundles_price_nanotons", table_name="nft_bundles")
    op.drop_index("ix_nft_bundles_created_at", table_name="nft_bundles")
    op.drop_index("ix_nft_bundles_seller_status", table_name="nft_bundles")
    op.drop_index("ix_nft_bundles_status", table_name="nft_bundles")
    op.drop_table("nft_bundles")
