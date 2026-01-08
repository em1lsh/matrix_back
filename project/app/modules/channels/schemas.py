"""Channels модуль - Schemas"""

from pydantic import BaseModel, Field

from app.api.schemas.channel import *


class ChannelBuyRequest(BaseModel):
    """Запрос на покупку канала"""

    receiver: str = Field(min_length=1, max_length=255, description="Username получателя (без @)")
    channel_id: int = Field(gt=0, description="ID канала")


__all__ = [
    "ChannelBuyRequest",
    "ChannelCreateRequest",
    "ChannelDealResponse",
    "ChannelGiftResponse",
    "ChannelResponse",
    "SelectChannelResponse",
]
