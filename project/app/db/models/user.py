from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.utils import slugify_str

from .base import Base


class User(Base):
    """
    Модель пользователя системы.

    Attributes:
        id: Telegram ID пользователя
        token: Токен для авторизации (уникальный)
        language: Язык интерфейса (по умолчанию 'en')
        payment_status: Статус оплаты
        subscription_status: Статус подписки
        payment_date: Дата последней оплаты
        subscription_date: Дата подписки
        registration_date: Дата регистрации (автоматически)
        memo: Уникальный memo для платежей
        market_balance: Баланс на маркете (в nanotons)
        group: Группа пользователя (member/admin/etc)
    """

    __tablename__ = "users"

    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # Authentication
    token: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, default=None)

    # User preferences
    language: Mapped[str] = mapped_column(String(32), default="en", index=True)

    # Payment and subscription
    payment_status: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    subscription_status: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    payment_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    subscription_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)

    # Timestamps
    registration_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Market
    memo: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    market_balance: Mapped[int] = mapped_column(BigInteger, default=0)
    frozen_balance: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Замороженный баланс (в nanotons) - средства в активных офферах",
    )

    # User role
    group: Mapped[str] = mapped_column(String(32), default="member", index=True)

    # Relationships
    accounts: Mapped[list["Account"]] = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    topups: Mapped[list["BalanceTopup"]] = relationship(
        "BalanceTopup", back_populates="user", cascade="all, delete-orphan"
    )
    channels: Mapped[list["Channel"]] = relationship("Channel", back_populates="user")
    purchases: Mapped[list["ChannelDeal"]] = relationship(
        "ChannelDeal", back_populates="buyer", foreign_keys="[ChannelDeal.buyer_id]"
    )
    sells: Mapped[list["ChannelDeal"]] = relationship(
        "ChannelDeal", back_populates="seller", foreign_keys="[ChannelDeal.seller_id]"
    )
    nfts: Mapped[list["NFT"]] = relationship("NFT", back_populates="user")
    offers: Mapped[list["NFTOffer"]] = relationship("NFTOffer", back_populates="user")
    buy_orders: Mapped[list["BuyOrder"]] = relationship("BuyOrder", back_populates="buyer")
    buy_order_deals_as_buyer: Mapped[list["BuyOrderDeal"]] = relationship(
        "BuyOrderDeal",
        back_populates="buyer",
        foreign_keys="[BuyOrderDeal.buyer_id]",
    )
    buy_order_deals_as_seller: Mapped[list["BuyOrderDeal"]] = relationship(
        "BuyOrderDeal",
        back_populates="seller",
        foreign_keys="[BuyOrderDeal.seller_id]",
    )
    nft_bundles: Mapped[list["NFTBundle"]] = relationship("NFTBundle", back_populates="seller")
    nft_order_logs: Mapped[list["NFTOrderEventLog"]] = relationship(
        "NFTOrderEventLog", back_populates="actor", foreign_keys="[NFTOrderEventLog.actor_user_id]"
    )
    bundle_offers: Mapped[list["NFTBundleOffer"]] = relationship(
        "NFTBundleOffer", back_populates="user", cascade="all, delete-orphan"
    )
    nft_presales: Mapped[list["NFTPreSale"]] = relationship(
        "NFTPreSale", back_populates="user", foreign_keys="[NFTPreSale.user_id]"
    )
    trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="user")
    tonnel_accounts: Mapped[list["TonnelAccount"]] = relationship("TonnelAccount", back_populates="user")
    tonnel_nfts: Mapped[list["TonnelNFT"]] = relationship("TonnelNFT", back_populates="user")

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_users_payment_subscription", "payment_status", "subscription_status"),
        Index("ix_users_group_payment", "group", "payment_status"),
    )


class BalanceTopup(Base):
    """
    Модель пополнения баланса маркета.

    Attributes:
        id: Уникальный идентификатор пополнения
        amount: Сумма пополнения (в nanotons)
        time: Время пополнения (строка для совместимости)
        user_id: ID пользователя
    """

    __tablename__ = "balance_topups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    time: Mapped[str] = mapped_column(String(255))

    # Foreign keys
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="topups")


class BalanceWithdraw(Base):
    """
    Модель вывода баланса маркета.

    Attributes:
        id: Уникальный идентификатор вывода
        amount: Сумма вывода (в nanotons)
        idempotency_key: Ключ идемпотентности для предотвращения дублирования
        user_id: ID пользователя
    """

    __tablename__ = "balance_withdraws"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Relationships
    user: Mapped["User"] = relationship("User")


class Account(Base):
    """
    Модель аккаунта Telegram для парсинга.

    Attributes:
        id: Уникальный идентификатор аккаунта (строка)
        is_active: Активен ли аккаунт
        phone: Номер телефона (уникальный)
        phone_code_hash: Хеш кода подтверждения
        password_hash: Хеш пароля (bcrypt)
        name: Имя аккаунта (уникальное)
        telegram_id: ID в Telegram (уникальный)
        stars_balance: Баланс звезд
        is_premium: Премиум статус
        user_id: ID владельца аккаунта
    """

    __tablename__ = "accounts"

    # Primary key
    id: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Authentication
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, default=None, index=True)
    phone_code_hash: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)

    # Account info
    name: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, default=None, index=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, default=None, index=True)

    # Premium features
    stars_balance: Mapped[int] = mapped_column(Integer, default=0)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="accounts")
    channels: Mapped[list["Channel"]] = relationship("Channel", back_populates="account")
    nfts: Mapped[list["NFT"]] = relationship("NFT", back_populates="account")
    tonnel_accounts: Mapped[list["TonnelAccount"]] = relationship("TonnelAccount", back_populates="account")

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_accounts_user_active", "user_id", "is_active"),
        Index("ix_accounts_active_premium", "is_active", "is_premium"),
    )

    def set_password(self, password: str) -> None:
        """
        Установить пароль (хеширует автоматически).

        Args:
            password: Пароль в открытом виде
        """
        from app.utils.security import hash_password

        self.password_hash = hash_password(password)

    def verify_password(self, password: str) -> bool:
        """
        Проверить пароль.

        Args:
            password: Пароль в открытом виде

        Returns:
            True если пароль верный, False иначе
        """
        if not self.password_hash:
            return False
        from app.utils.security import verify_password

        return verify_password(password, self.password_hash)


class Gift(Base):
    """
    Модель подарка (NFT) в Telegram.

    Attributes:
        id: Уникальный идентификатор подарка
        image: URL изображения
        title: Название подарка
        num: Номер подарка
        model_name: Название модели
        pattern_name: Название паттерна
        backdrop_name: Название фона
        model_rarity: Редкость модели (0-1)
        pattern_rarity: Редкость паттерна (0-1)
        backdrop_rarity: Редкость фона (0-1)
        center_color: Цвет центра (hex)
        edge_color: Цвет края (hex)
        pattern_color: Цвет паттерна (hex)
        text_color: Цвет текста (hex)
        availability_total: Общее количество доступных
    """

    __tablename__ = "gifts"

    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # Media
    image: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)

    # Basic info
    title: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None, index=True)
    num: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None, index=True)

    # Design components
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    pattern_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    backdrop_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)

    # Rarity scores
    model_rarity: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    pattern_rarity: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    backdrop_rarity: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)

    # Colors
    center_color: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    edge_color: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    pattern_color: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    text_color: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)

    # Availability
    availability_total: Mapped[int] = mapped_column(Integer, default=0, index=True)

    # Relationships
    channel_gifts: Mapped[list["ChannelGift"]] = relationship("ChannelGift", back_populates="gift")
    nfts: Mapped[list["NFT"]] = relationship("NFT", back_populates="gift")
    nft_deals: Mapped[list["NFTDeal"]] = relationship("NFTDeal", back_populates="gift")
    nft_presales: Mapped[list["NFTPreSale"]] = relationship("NFTPreSale", back_populates="gift")

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_gifts_title_num", "title", "num"),
        Index("ix_gifts_availability", "availability_total"),
    )

    def get_telegram_url(self) -> str:
        """
        Получить URL подарка в Telegram.

        Returns:
            URL вида https://t.me/nft/title-num
        """
        parsed_title = slugify_str(str(self.title))
        num = int(self.num) if self.num else 0
        return f"https://t.me/nft/{parsed_title}-{num}"
