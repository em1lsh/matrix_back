from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from .base import Base


"""
Таблица trades - nfts
"""
trade_nfts_table = Table(
    "trade_nfts",
    Base.metadata,
    Column("trade_id", Integer, ForeignKey("trades.id")),
    Column("nft_id", Integer, ForeignKey("nfts.id")),
)


"""
Таблица trade applications - nfts
"""
trade_application_nfts_table = Table(
    "trade_application_nfts",
    Base.metadata,
    Column("trade_application_id", Integer, ForeignKey("trade_applications.id")),
    Column("nft_id", Integer, ForeignKey("nfts.id")),
)


"""
Таблица trade deals - gifts (sended)
"""
trade_deal_sended_gifts_table = Table(
    "trade_deal_sended_gifts",
    Base.metadata,
    Column("trade_deal_id", Integer, ForeignKey("trade_deals.id")),
    Column("gift_id", BigInteger, ForeignKey("gifts.id")),
)


"""
Таблица trade deals - gifts (gived)
"""
trade_deal_gived_gifts_table = Table(
    "trade_deal_gived_gifts",
    Base.metadata,
    Column("trade_deal_id", Integer, ForeignKey("trade_deals.id")),
    Column("gift_id", BigInteger, ForeignKey("gifts.id")),
)


class Trade(Base):
    """
    Модель трейда
    """

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    user = relationship("User", back_populates="trades")

    reciver_id = Column(BigInteger, nullable=True, default=None)  # если трейд персональный для какого-то юзера

    nfts = relationship("NFT", secondary=trade_nfts_table)
    requirements = relationship("TradeRequirement", back_populates="trade")
    proposals = relationship("TradeProposal", back_populates="trade")


class TradeRequirement(Base):
    """
    Модель того что человек запрашивает при трейде
    """

    __tablename__ = "trade_requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)

    trade_id = Column(BigInteger, ForeignKey("trades.id", ondelete="CASCADE"))
    trade = relationship("Trade", back_populates="requirements")

    collection = Column(String(64))
    backdrop = Column(String(64), nullable=True, default=None)


class TradeProposal(Base):
    """
    Модель предложения на трейд
    """

    __tablename__ = "trade_applications"

    id = Column(Integer, primary_key=True, autoincrement=True)

    trade_id = Column(BigInteger, ForeignKey("trades.id", ondelete="CASCADE"))
    trade = relationship("Trade", back_populates="proposals")

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))

    nfts = relationship("NFT", secondary=trade_application_nfts_table)


class TradeDeal(Base):
    """
    Модель трейда в истории покупок
    """

    __tablename__ = "trade_deals"

    id = Column(Integer, primary_key=True, autoincrement=True)

    seller_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    buyer_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))

    sended = relationship("Gift", secondary=trade_deal_sended_gifts_table)
    gived = relationship("Gift", secondary=trade_deal_gived_gifts_table)
