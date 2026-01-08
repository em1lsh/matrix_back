from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class NFT(Base):
    """
    Модель NFT на локальном маркете.

    Attributes:
        id: Уникальный идентификатор NFT
        gift_id: ID подарка
        user_id: ID владельца
        account_id: ID аккаунта (опционально)
        msg_id: ID сообщения в Telegram
        price: Цена продажи (NULL = не на продаже)
    """

    __tablename__ = "nfts"
    __table_args__ = (
        Index("ix_nfts_user_price", "user_id", "price"),
        Index("ix_nfts_gift_price", "gift_id", "price"),
        Index("ix_nfts_price_not_null", "price", postgresql_where=text("price IS NOT NULL")),
        Index("ix_nfts_active_bundle_id", "active_bundle_id"),
        CheckConstraint("price IS NULL OR price > 0", name="check_nft_price_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gift_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("gifts.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[str | None] = mapped_column(
        String(255), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    msg_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    price: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True, comment="Цена в nanotons (NULL = не на продаже)"
    )
    active_bundle_id: Mapped[int | None] = mapped_column(
        ForeignKey("nft_bundles.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    gift: Mapped["Gift"] = relationship("Gift", back_populates="nfts", lazy="selectin")
    user: Mapped["User"] = relationship("User", back_populates="nfts")
    account: Mapped[Optional["Account"]] = relationship("Account", back_populates="nfts")
    offers: Mapped[list["NFTOffer"]] = relationship(
        "NFTOffer", back_populates="nft", cascade="all, delete-orphan", lazy="noload"
    )
    active_bundle: Mapped[Optional["NFTBundle"]] = relationship(
        "NFTBundle", back_populates="nfts", foreign_keys=[active_bundle_id]
    )
    bundle_items: Mapped[list["NFTBundleItem"]] = relationship(
        "NFTBundleItem", back_populates="nft", cascade="all, delete-orphan", lazy="noload"
    )


class NFTDeal(Base):
    """
    Сделка по NFT на маркете.

    Attributes:
        id: Уникальный идентификатор сделки
        gift_id: ID подарка
        seller_id: ID продавца
        buyer_id: ID покупателя
        price: Цена сделки
    """

    __tablename__ = "nft_deals"
    __table_args__ = (
        Index("ix_nft_deals_seller_buyer", "seller_id", "buyer_id"),
        Index("ix_nft_deals_gift_price", "gift_id", "price"),
        Index("ix_nft_deals_created_at", "created_at"),
        CheckConstraint("price > 0", name="check_nft_deal_price_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gift_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("gifts.id"), nullable=False, index=True)
    seller_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    buyer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    price: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="Цена в nanotons")

    # Relationships
    gift: Mapped["Gift"] = relationship("Gift", back_populates="nft_deals", lazy="selectin")


class NFTOffer(Base):
    """
    Модель предложения цены за NFT.

    Attributes:
        id: Уникальный идентификатор предложения
        nft_id: ID NFT
        user_id: ID пользователя, сделавшего предложение
        price: Предложенная цена
        reciprocal_price: Встречная цена
        updated: Время последнего обновления
    """

    __tablename__ = "nft_orders"
    __table_args__ = (
        Index("ix_nft_offers_nft_user", "nft_id", "user_id"),
        Index("ix_nft_offers_updated", "updated"),
        CheckConstraint("price > 0", name="check_nft_offer_price_positive"),
        CheckConstraint(
            "reciprocal_price IS NULL OR reciprocal_price > 0", name="check_nft_offer_reciprocal_price_positive"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nft_id: Mapped[int] = mapped_column(ForeignKey("nfts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="Предложенная цена")
    reciprocal_price: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="Встречная цена")
    updated: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, index=True
    )

    # Relationships
    nft: Mapped["NFT"] = relationship("NFT", back_populates="offers", lazy="selectin")
    user: Mapped["User"] = relationship("User", back_populates="offers", lazy="selectin")


class NFTPreSale(Base):
    """
    Модель пресейла NFT.

    Attributes:
        id: Уникальный идентификатор пресейла
        gift_id: ID подарка
        user_id: ID продавца
        buyer_id: ID покупателя
        price: Цена пресейла
        transfer_time: Время передачи (Unix timestamp)
    """

    __tablename__ = "nft_presales"
    __table_args__ = (
        Index("ix_nft_presales_user_buyer", "user_id", "buyer_id"),
        Index("ix_nft_presales_transfer_time", "transfer_time"),
        CheckConstraint("price IS NULL OR price > 0", name="check_nft_presale_price_positive"),
        CheckConstraint("transfer_time > 0", name="check_nft_presale_transfer_time_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gift_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("gifts.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    buyer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    price: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True, comment="Цена в nanotons")
    transfer_time: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="Unix timestamp")

    # Relationships
    gift: Mapped["Gift"] = relationship("Gift", back_populates="nft_presales", lazy="selectin")
    user: Mapped["User"] = relationship("User", back_populates="nft_presales", foreign_keys=[user_id])
