"""Add bundle offers and log linkage

Revision ID: 20251227_bundle_offers
Revises: 20251227_bundles
Create Date: 2025-12-27

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251227_bundle_offers"
down_revision = "20251227_bundles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nft_bundle_offers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bundle_id", sa.Integer(), sa.ForeignKey("nft_bundles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price", sa.BigInteger(), nullable=False),
        sa.Column("reciprocal_price", sa.BigInteger(), nullable=True),
        sa.Column("updated", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("price > 0", name="check_bundle_offer_price_positive"),
        sa.CheckConstraint(
            "reciprocal_price IS NULL OR reciprocal_price > 0",
            name="check_bundle_offer_reciprocal_price_positive",
        ),
    )
    op.create_index("ix_bundle_offers_bundle_user", "nft_bundle_offers", ["bundle_id", "user_id"])
    op.create_index("ix_bundle_offers_updated", "nft_bundle_offers", ["updated"])

    op.add_column(
        "nft_order_event_logs",
        sa.Column(
            "bundle_offer_id",
            sa.Integer(),
            sa.ForeignKey("nft_bundle_offers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_nft_order_event_logs_bundle_offer_id", "nft_order_event_logs", ["bundle_offer_id"])


def downgrade() -> None:
    op.drop_index("ix_nft_order_event_logs_bundle_offer_id", table_name="nft_order_event_logs")
    op.drop_column("nft_order_event_logs", "bundle_offer_id")
    op.drop_index("ix_bundle_offers_updated", table_name="nft_bundle_offers")
    op.drop_index("ix_bundle_offers_bundle_user", table_name="nft_bundle_offers")
    op.drop_table("nft_bundle_offers")
