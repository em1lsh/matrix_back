from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Auction(Base):
    """
    Модель аукциона NFT.

    Attributes:
        id: Уникальный идентификатор аукциона
        nft_id: ID NFT на аукционе
        user_id: ID создателя аукциона
        start_bid: Начальная ставка
        step_bid: Шаг ставки (в процентах)
        last_bid: Последняя ставка
        expired_at: Время окончания аукциона
    """

    __tablename__ = "auctions"
    __table_args__ = (
        Index("ix_auctions_expired_at", "expired_at"),
        Index("ix_auctions_user_expired", "user_id", "expired_at"),
        CheckConstraint("start_bid > 0", name="check_auction_start_bid_positive"),
        CheckConstraint("step_bid > 0 AND step_bid <= 100", name="check_auction_step_bid_range"),
        CheckConstraint("last_bid IS NULL OR last_bid >= start_bid", name="check_auction_last_bid_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nft_id: Mapped[int] = mapped_column(ForeignKey("nfts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_bid: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, comment="Начальная ставка в nanotons"
    )
    step_bid: Mapped[float] = mapped_column(Float, default=10.0, nullable=False, comment="Шаг ставки в процентах")
    last_bid: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True, comment="Последняя ставка в nanotons"
    )
    expired_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True, comment="Время окончания аукциона"
    )

    # Relationships
    nft: Mapped["NFT"] = relationship("NFT", foreign_keys=[nft_id], lazy="selectin")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    bids: Mapped[list["AuctionBid"]] = relationship(
        "AuctionBid", back_populates="auction", cascade="all, delete-orphan", lazy="noload"
    )


class AuctionBid(Base):
    """
    Модель ставки на аукционе.

    Attributes:
        id: Уникальный идентификатор ставки
        auction_id: ID аукциона
        user_id: ID пользователя, сделавшего ставку
        bid: Размер ставки
    """

    __tablename__ = "auction_bids"
    __table_args__ = (
        Index("ix_auction_bids_auction_user", "auction_id", "user_id"),
        Index("ix_auction_bids_auction_bid", "auction_id", "bid"),
        Index("ix_auction_bids_created_at", "created_at"),
        CheckConstraint("bid > 0", name="check_auction_bid_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    auction_id: Mapped[int | None] = mapped_column(
        ForeignKey("auctions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bid: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="Размер ставки в nanotons")

    # Relationships
    auction: Mapped[Optional["Auction"]] = relationship("Auction", back_populates="bids")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class AuctionDeal(Base):
    """
    Модель завершенной сделки на аукционе.

    Attributes:
        id: Уникальный идентификатор сделки
        gift_id: ID подарка
        seller_id: ID продавца
        buyer_id: ID покупателя
        price: Финальная цена
    """

    __tablename__ = "auction_deals"
    __table_args__ = (
        Index("ix_auction_deals_seller_buyer", "seller_id", "buyer_id"),
        Index("ix_auction_deals_gift_price", "gift_id", "price"),
        Index("ix_auction_deals_created_at", "created_at"),
        CheckConstraint("price > 0", name="check_auction_deal_price_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gift_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("gifts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seller_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    buyer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    price: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="Финальная цена в nanotons")

    # Relationships
    gift: Mapped["Gift"] = relationship("Gift", foreign_keys=[gift_id], lazy="selectin")
