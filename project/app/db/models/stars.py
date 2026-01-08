"""Модели для покупки звёзд и премиума через Fragment"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class StarsPurchase(Base):
    """
    Модель покупки звёзд через Fragment API.

    Attributes:
        id: Уникальный идентификатор покупки
        user_id: ID пользователя, который купил звёзды
        recipient_username: Username получателя звёзд (без @)
        stars_amount: Количество купленных звёзд
        price_nanotons: Цена в nanotons, которую заплатил пользователь
        fragment_cost_ton: Реальная стоимость в TON по Fragment API
        fragment_tx_id: ID транзакции Fragment (если есть)
        status: Статус покупки (pending, completed, failed)
        error_message: Сообщение об ошибке (если есть)
    """

    __tablename__ = "stars_purchases"
    __table_args__ = (
        Index("ix_stars_purchases_user_created", "user_id", "created_at"),
        Index("ix_stars_purchases_status", "status"),
        Index("ix_stars_purchases_recipient", "recipient_username"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_username: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    stars_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    price_nanotons: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="Цена в nanotons")
    fragment_cost_ton: Mapped[float | None] = mapped_column(nullable=True, comment="Реальная стоимость Fragment")
    fragment_tx_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")


class PremiumPurchase(Base):
    """
    Модель покупки Telegram Premium через Fragment API.

    Attributes:
        id: Уникальный идентификатор покупки
        user_id: ID пользователя, который купил премиум
        recipient_username: Username получателя премиума (без @)
        months: Количество месяцев подписки (3, 6 или 12)
        show_sender: Показывать отправителя
        price_nanotons: Цена в nanotons, которую заплатил пользователь
        ton_price: Цена в TON от Fragment
        fragment_tx_id: UUID транзакции Fragment
        ref_id: Reference ID от Fragment
        status: Статус покупки (pending, completed, failed)
        error_message: Сообщение об ошибке (если есть)
        fragment_response: Полный JSON ответ от Fragment (для отладки)
    """

    __tablename__ = "premium_purchases"
    __table_args__ = (
        Index("ix_premium_purchases_user_created", "user_id", "created_at"),
        Index("ix_premium_purchases_status", "status"),
        Index("ix_premium_purchases_recipient", "recipient_username"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_username: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    months: Mapped[int] = mapped_column(Integer, nullable=False, comment="Месяцев подписки (3, 6, 12)")
    show_sender: Mapped[bool] = mapped_column(Boolean, default=False)
    price_nanotons: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="Цена в nanotons")
    ton_price: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Цена в TON от Fragment")
    fragment_tx_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True, comment="UUID транзакции")
    ref_id: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Reference ID")
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fragment_response: Mapped[str | None] = mapped_column(String(2000), nullable=True, comment="JSON ответ Fragment")

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")
