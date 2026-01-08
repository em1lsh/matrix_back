from sqlalchemy import BigInteger, CheckConstraint, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Market(Base):
    """
    Модель маркета.

    Attributes:
        id: Уникальный идентификатор маркета
        title: Название маркета (уникальное)
        logo: URL логотипа маркета
    """

    __tablename__ = "markets"
    __table_args__ = (Index("ix_markets_title", "title", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment="Название маркета")
    logo: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="URL логотипа")

    # Relationships
    floors: Mapped[list["MarketFloor"]] = relationship(
        "MarketFloor", back_populates="market", cascade="all, delete-orphan", lazy="noload"
    )


class MarketFloor(Base):
    """
    Модель для графика цены коллекции NFT.

    Attributes:
        id: Уникальный идентификатор записи
        name: Имя модели или коллекции
        price_nanotons: Цена в nanotons
        price_dollars: Цена в долларах
        price_rubles: Цена в рублях
        market_id: ID маркета
    """

    __tablename__ = "market_nft_floors"
    __table_args__ = (
        Index("ix_market_nft_floors_market_id", "market_id"),
        Index("ix_market_nft_floors_name", "name"),
        Index("ix_market_nft_floors_created_at", "created_at"),
        CheckConstraint("price_nanotons >= 0", name="check_market_floor_price_nanotons_positive"),
        CheckConstraint("price_dollars >= 0", name="check_market_floor_price_dollars_positive"),
        CheckConstraint("price_rubles >= 0", name="check_market_floor_price_rubles_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Имя модели или коллекции")
    price_nanotons: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="Цена в nanotons")
    price_dollars: Mapped[float] = mapped_column(Float, nullable=False, comment="Цена в долларах")
    price_rubles: Mapped[float] = mapped_column(Float, nullable=False, comment="Цена в рублях")
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    market: Mapped["Market"] = relationship("Market", back_populates="floors")
