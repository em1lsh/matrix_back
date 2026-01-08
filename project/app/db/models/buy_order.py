from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from .base import Base


class BuyOrderStatus:
    ACTIVE = "ACTIVE"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


class BuyOrderDealSource:
    AUTO_MATCH = "AUTO_MATCH"
    MANUAL_SELL = "MANUAL_SELL"


class BuyOrder(Base):
    """Лимитный ордер на покупку NFT по коллекции"""

    __tablename__ = "buy_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    buyer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    pattern_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    backdrop_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    price_limit: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    quantity_total: Mapped[int] = mapped_column(nullable=False)
    quantity_remaining: Mapped[int] = mapped_column(nullable=False, index=True)
    frozen_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default=BuyOrderStatus.ACTIVE)

    buyer: Mapped["User"] = relationship("User", back_populates="buy_orders", lazy="selectin")
    deals: Mapped[list["BuyOrderDeal"]] = relationship(
        "BuyOrderDeal", back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    @declared_attr.directive
    def __table_args__(cls):
        return (
            CheckConstraint("quantity_total > 0", name="check_buy_order_quantity_positive"),
            CheckConstraint("quantity_remaining >= 0", name="check_buy_order_quantity_remaining_non_negative"),
            CheckConstraint("price_limit > 0", name="check_buy_order_price_positive"),
            CheckConstraint("frozen_amount >= 0", name="check_buy_order_frozen_amount_non_negative"),
            Index(
                "ix_buy_orders_title_status_price_created",
                cls.title,
                cls.status,
                cls.price_limit.desc(),
                cls.created_at.asc(),
            ),
            Index(
                "ix_buy_orders_title_model_pattern_backdrop",
                cls.title,
                cls.model_name,
                cls.pattern_name,
                cls.backdrop_name,
            ),
        )


class BuyOrderDeal(Base):
    """Лог исполненных сделок по ордерам"""

    __tablename__ = "buy_order_deals"
    __table_args__ = (
        Index("ix_buy_order_deals_order_nft", "order_id", "nft_id"),
        Index("ix_buy_order_deals_buyer_seller", "buyer_id", "seller_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("buy_orders.id", ondelete="CASCADE"), index=True)
    nft_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("nfts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    gift_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("gifts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    buyer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    seller_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reserved_unit_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    execution_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    commission: Mapped[int] = mapped_column(BigInteger, nullable=False)
    seller_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    nft_deal_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("nft_deals.id", ondelete="SET NULL"), nullable=True, index=True
    )

    order: Mapped["BuyOrder"] = relationship("BuyOrder", back_populates="deals", lazy="selectin")
    nft: Mapped["NFT"] = relationship("NFT", lazy="selectin")
    buyer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[buyer_id], back_populates="buy_order_deals_as_buyer", lazy="selectin"
    )
    seller: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[seller_id], back_populates="buy_order_deals_as_seller", lazy="selectin"
    )
    gift: Mapped["Gift"] = relationship("Gift", lazy="selectin")
