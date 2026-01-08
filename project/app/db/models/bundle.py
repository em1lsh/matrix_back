from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class NFTBundle(Base):
    __tablename__ = "nft_bundles"
    __table_args__ = (
        Index("ix_nft_bundles_status", "status"),
        Index("ix_nft_bundles_seller_status", "seller_id", "status"),
        Index("ix_nft_bundles_created_at", "created_at"),
        Index("ix_nft_bundles_price_nanotons", "price_nanotons"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    seller_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    price_nanotons: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    seller: Mapped["User"] = relationship("User", back_populates="nft_bundles")
    items: Mapped[list["NFTBundleItem"]] = relationship(
        "NFTBundleItem", back_populates="bundle", cascade="all, delete-orphan", lazy="selectin"
    )
    nfts: Mapped[list["NFT"]] = relationship("NFT", back_populates="active_bundle", lazy="selectin")
    bundle_offers: Mapped[list["NFTBundleOffer"]] = relationship(
        "NFTBundleOffer", back_populates="bundle", cascade="all, delete-orphan", lazy="noload"
    )


class NFTBundleItem(Base):
    __tablename__ = "nft_bundle_items"
    __table_args__ = (
        UniqueConstraint("bundle_id", "nft_id", name="uq_nft_bundle_items_bundle_nft"),
        Index("ix_nft_bundle_items_nft_id", "nft_id"),
        Index("ix_nft_bundle_items_bundle_id", "bundle_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bundle_id: Mapped[int] = mapped_column(ForeignKey("nft_bundles.id", ondelete="CASCADE"), nullable=False)
    nft_id: Mapped[int] = mapped_column(ForeignKey("nfts.id", ondelete="RESTRICT"), nullable=False)

    bundle: Mapped[NFTBundle] = relationship("NFTBundle", back_populates="items")
    nft: Mapped["NFT"] = relationship("NFT", back_populates="bundle_items")