from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class NFTOrderEventLog(Base):
    __tablename__ = "nft_order_event_logs"
    __table_args__ = (
        Index("ix_nft_order_event_logs_offer_id", "offer_id"),
        Index("ix_nft_order_event_logs_nft_id", "nft_id"),
        Index("ix_nft_order_event_logs_event_type", "event_type"),
        Index("ix_nft_order_event_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    offer_id: Mapped[int | None] = mapped_column(
        ForeignKey("nft_orders.id", ondelete="SET NULL"), nullable=True
    )
    nft_id: Mapped[int | None] = mapped_column(
        ForeignKey("nfts.id", ondelete="SET NULL"), nullable=True
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    counterparty_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    bundle_offer_id: Mapped[int | None] = mapped_column(
        ForeignKey("nft_bundle_offers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    amount_nanotons: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    offer: Mapped["NFTOffer | None"] = relationship("NFTOffer", lazy="selectin")
    nft: Mapped["NFT | None"] = relationship("NFT", lazy="selectin")
    actor: Mapped["User | None"] = relationship(
        "User", foreign_keys=[actor_user_id], lazy="selectin", back_populates="nft_order_logs"
    )
    counterparty: Mapped["User | None"] = relationship(
        "User", foreign_keys=[counterparty_user_id], lazy="selectin"
    )