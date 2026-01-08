from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class NFTBundleOffer(Base):
    __tablename__ = "nft_bundle_offers"
    __table_args__ = (
        Index("ix_bundle_offers_bundle_user", "bundle_id", "user_id"),
        Index("ix_bundle_offers_updated", "updated"),
        CheckConstraint("price > 0", name="check_bundle_offer_price_positive"),
        CheckConstraint(
            "reciprocal_price IS NULL OR reciprocal_price > 0",
            name="check_bundle_offer_reciprocal_price_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bundle_id: Mapped[int] = mapped_column(
        ForeignKey("nft_bundles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="Предложенная цена")
    reciprocal_price: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="Встречная цена")
    updated: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
    )

    bundle: Mapped["NFTBundle"] = relationship("NFTBundle", back_populates="bundle_offers", lazy="selectin")
    user: Mapped["User"] = relationship("User", back_populates="bundle_offers", lazy="selectin")