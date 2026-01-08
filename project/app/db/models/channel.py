from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from .base import Base


class Channel(Base):
    __tablename__ = "channels"

    id = Column(BigInteger, primary_key=True)
    title = Column(String(255))
    username = Column(String(255), nullable=True)
    price = Column(BigInteger, nullable=True, default=None)
    gifts_hash = Column(String(255))

    account_id = Column(String(255), ForeignKey("accounts.id", ondelete="CASCADE"))
    account = relationship("Account", back_populates="channels")

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    user = relationship("User", back_populates="channels", foreign_keys=[user_id])

    channel_gifts = relationship("ChannelGift", back_populates="channel")


DealGift = Table(
    "deals_gifts",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("deal_id", Integer, ForeignKey("channel_deals.id")),
    Column("gift_id", Integer, ForeignKey("channels_gifts.id")),
)


class ChannelGift(Base):
    __tablename__ = "channels_gifts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quantity = Column(Integer, default=1)

    gift_id = Column(BigInteger, ForeignKey("gifts.id", ondelete="CASCADE"))
    gift = relationship("Gift", back_populates="channel_gifts")

    channel_id = Column(BigInteger, ForeignKey("channels.id", ondelete="SET NULL"))
    channel = relationship("Channel", back_populates="channel_gifts")

    deals = relationship("ChannelDeal", secondary=DealGift, back_populates="deal_gifts")


class ChannelDeal(Base):
    __tablename__ = "channel_deals"

    id = Column(Integer, primary_key=True, autoincrement=True)

    title = Column(String(255))
    username = Column(String(255), nullable=True)
    deal_gifts = relationship("ChannelGift", secondary=DealGift, back_populates="deals")
    price = Column(BigInteger)

    buyer_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, default=None)
    buyer = relationship("User", back_populates="purchases", foreign_keys=[buyer_id])

    seller_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, default=None)
    seller = relationship("User", back_populates="sells", foreign_keys=[seller_id])
