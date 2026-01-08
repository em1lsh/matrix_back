"""Модели для системы продвижения NFT"""

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class PromotedNFT(Base):
    """
    Модель продвижения NFT.

    Attributes:
        id: Уникальный идентификатор продвижения
        nft_id: ID NFT
        user_id: ID пользователя
        created_at: Время создания продвижения
        ends_at: Время окончания продвижения
        total_costs: Общая стоимость продвижения (в nanotons)
        is_active: Активно ли продвижение
    """

    __tablename__ = "promoted_nfts"
    __table_args__ = (
        Index("ix_promoted_nfts_nft_active", "nft_id", "is_active"),
        Index("ix_promoted_nfts_user_active", "user_id", "is_active"),
        Index("ix_promoted_nfts_ends_at", "ends_at"),
        Index("ix_promoted_nfts_active", "is_active"),
        # Уникальный индекс для активных продвижений
        Index("ix_promoted_nfts_unique_active", "nft_id", unique=True, 
              postgresql_where=text("is_active = true")),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nft_id: Mapped[int] = mapped_column(
        ForeignKey("nfts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    total_costs: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Общая стоимость продвижения в nanotons"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    nft: Mapped["NFT"] = relationship("NFT", lazy="selectin")
    user: Mapped["User"] = relationship("User", lazy="selectin")