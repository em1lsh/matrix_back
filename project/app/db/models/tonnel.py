from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class TonnelAccount(Base):
    """
    Модель аккаунта Tonnel Market с данными аутентификации.

    Attributes:
        id: Уникальный идентификатор аккаунта
        user_id: ID пользователя
        account_id: ID Telegram аккаунта для парсинга
        auth_data: DEPRECATED - старое поле с незашифрованными данными
        auth_data_encrypted: Зашифрованные данные аутентификации
        is_active: Активен ли аккаунт
    """

    __tablename__ = "tonnel_accounts"
    __table_args__ = (
        Index("ix_tonnel_accounts_user_id", "user_id"),
        Index("ix_tonnel_accounts_account_id", "account_id"),
        Index("ix_tonnel_accounts_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[str] = mapped_column(String(255), ForeignKey("accounts.id"), nullable=False)

    # DEPRECATED: auth_data - use auth_data_encrypted instead
    auth_data: Mapped[str | None] = mapped_column(Text, nullable=True, comment="DEPRECATED - use auth_data_encrypted")
    auth_data_encrypted: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Encrypted auth data with Fernet"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="tonnel_accounts")
    account: Mapped["Account"] = relationship("Account", back_populates="tonnel_accounts")
    nfts: Mapped[list["TonnelNFT"]] = relationship(
        "TonnelNFT", back_populates="tonnel_account", cascade="all, delete-orphan", lazy="noload"
    )
    offers: Mapped[list["TonnelOffer"]] = relationship(
        "TonnelOffer", back_populates="tonnel_account", cascade="all, delete-orphan", lazy="noload"
    )
    activities: Mapped[list["TonnelActivity"]] = relationship(
        "TonnelActivity", back_populates="tonnel_account", cascade="all, delete-orphan", lazy="noload"
    )

    def set_auth_data(self, auth_data: str):
        """Установить auth_data (шифрует автоматически)"""
        from app.utils.security import encrypt_data

        self.auth_data_encrypted = encrypt_data(auth_data)

    def get_auth_data(self) -> str:
        """Получить auth_data (расшифровывает автоматически)"""
        # Для обратной совместимости: если есть старое поле, используем его
        if self.auth_data and not self.auth_data_encrypted:
            return self.auth_data

        if not self.auth_data_encrypted:
            return ""

        from app.utils.security import decrypt_data

        return decrypt_data(self.auth_data_encrypted)


class TonnelNFT(Base):
    """
    Модель NFT на Tonnel Market.

    Attributes:
        id: Уникальный идентификатор NFT
        tonnel_account_id: ID аккаунта Tonnel
        user_id: ID пользователя-владельца
        gift_id: ID подарка в Tonnel
        gift_num: Номер подарка в Telegram
        gift_name: Название подарка
        status: Статус NFT (listed, unlisted, sold)
    """

    __tablename__ = "tonnel_nfts"
    __table_args__ = (
        Index("ix_tonnel_nfts_tonnel_account_id", "tonnel_account_id"),
        Index("ix_tonnel_nfts_user_id", "user_id"),
        Index("ix_tonnel_nfts_gift_id", "gift_id"),
        Index("ix_tonnel_nfts_status", "status"),
        Index("ix_tonnel_nfts_price", "price"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tonnel_account_id: Mapped[int] = mapped_column(ForeignKey("tonnel_accounts.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Данные NFT из Tonnel API
    gift_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="ID подарка в Tonnel")
    gift_num: Mapped[int | None] = mapped_column(nullable=True, comment="Номер подарка в Telegram")
    gift_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Название подарка")

    # Атрибуты NFT
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_rarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(255), nullable=True)
    symbol_rarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    backdrop: Mapped[str | None] = mapped_column(String(255), nullable=True)
    backdrop_rarity: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Цена и статус
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    asset: Mapped[str] = mapped_column(
        String(10), nullable=False, default="TON", server_default="TON", comment="TON, USDT, TONNEL"
    )
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="listed, unlisted, sold")
    listed_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    sold_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    # Дополнительные данные
    custom_emoji_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    premarket: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    telegram_marketplace: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    mintable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    bundle: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    # Relationships
    tonnel_account: Mapped["TonnelAccount"] = relationship("TonnelAccount", back_populates="nfts")
    user: Mapped["User"] = relationship("User", back_populates="tonnel_nfts")
    offers: Mapped[list["TonnelOffer"]] = relationship("TonnelOffer", back_populates="tonnel_nft", lazy="noload")


class TonnelOffer(Base):
    """
    Модель оффера на Tonnel Market.

    Attributes:
        id: Уникальный идентификатор оффера
        tonnel_account_id: ID аккаунта Tonnel
        tonnel_nft_id: ID NFT (если оффер на конкретный NFT)
        offer_type: Тип оффера (gift_offer, collection_offer, auction)
        amount: Сумма оффера
        asset: Валюта (TON, USDT, TONNEL)
        status: Статус (active, cancelled, expired, completed)
    """

    __tablename__ = "tonnel_offers"
    __table_args__ = (
        Index("ix_tonnel_offers_tonnel_account_id", "tonnel_account_id"),
        Index("ix_tonnel_offers_tonnel_nft_id", "tonnel_nft_id"),
        Index("ix_tonnel_offers_offer_type", "offer_type"),
        Index("ix_tonnel_offers_status", "status"),
        Index("ix_tonnel_offers_gift_id", "gift_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tonnel_account_id: Mapped[int] = mapped_column(ForeignKey("tonnel_accounts.id"), nullable=False)
    tonnel_nft_id: Mapped[int | None] = mapped_column(ForeignKey("tonnel_nfts.id"), nullable=True)

    # Данные оффера
    offer_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="gift_offer, collection_offer, auction")
    gift_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="ID подарка для которого оффер")
    auction_id: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="ID аукциона")

    # Для collection offers
    gift_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    backdrop: Mapped[str | None] = mapped_column(String(255), nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(255), nullable=True)

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    asset: Mapped[str] = mapped_column(String(10), nullable=False, default="TON", server_default="TON")
    max_nfts: Mapped[int | None] = mapped_column(nullable=True)
    current_nfts: Mapped[int | None] = mapped_column(nullable=True)

    status: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="active, cancelled, expired, completed"
    )
    expires_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    tonnel_account: Mapped["TonnelAccount"] = relationship("TonnelAccount", back_populates="offers")
    tonnel_nft: Mapped[Optional["TonnelNFT"]] = relationship("TonnelNFT", back_populates="offers")


class TonnelActivity(Base):
    """
    Модель активности на Tonnel Market.

    Attributes:
        id: Уникальный идентификатор активности
        tonnel_account_id: ID аккаунта Tonnel
        activity_type: Тип активности (buy, sell, listing, price_update, offer, bid)
        amount: Сумма транзакции
        asset: Валюта (TON, USDT, TONNEL)
    """

    __tablename__ = "tonnel_activities"
    __table_args__ = (
        Index("ix_tonnel_activities_tonnel_account_id", "tonnel_account_id"),
        Index("ix_tonnel_activities_activity_type", "activity_type"),
        Index("ix_tonnel_activities_gift_id", "gift_id"),
        Index("ix_tonnel_activities_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tonnel_account_id: Mapped[int] = mapped_column(ForeignKey("tonnel_accounts.id"), nullable=False)

    # Данные активности
    activity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="buy, sell, listing, price_update, offer, bid"
    )
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    asset: Mapped[str] = mapped_column(String(10), nullable=False, default="TON", server_default="TON")

    # Связанные данные
    gift_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    gift_num: Mapped[int | None] = mapped_column(nullable=True)
    gift_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    backdrop: Mapped[str | None] = mapped_column(String(255), nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Дополнительные данные
    buyer_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    seller_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    auction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    tonnel_account: Mapped["TonnelAccount"] = relationship("TonnelAccount", back_populates="activities")


class TonnelBalance(Base):
    """
    Модель баланса на Tonnel Market.

    Attributes:
        id: Уникальный идентификатор баланса
        tonnel_account_id: ID аккаунта Tonnel
        asset: Валюта (TON, USDT, TONNEL)
        balance: Доступный баланс
        frozen_funds: Замороженные средства
    """

    __tablename__ = "tonnel_balances"
    __table_args__ = (
        Index("ix_tonnel_balances_tonnel_account_id", "tonnel_account_id"),
        Index("ix_tonnel_balances_asset", "asset"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tonnel_account_id: Mapped[int] = mapped_column(ForeignKey("tonnel_accounts.id"), nullable=False)

    asset: Mapped[str] = mapped_column(String(10), nullable=False, comment="TON, USDT, TONNEL")
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    frozen_funds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")

    # Relationships
    tonnel_account: Mapped["TonnelAccount"] = relationship("TonnelAccount")
