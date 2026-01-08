"""Accounts модуль - Schemas"""

from pydantic import BaseModel

from app.api.schemas.account import AccountCreateRequest, AccountResponse, ApproveRequest
from app.api.schemas.nft import NFTResponse


# Alias для совместимости с router
ApproveAuthRequest = ApproveRequest


class SelectChannelResponse(BaseModel):
    """Информация о канале для выбора"""

    id: int
    title: str
    username: str | None = None


class SendGiftsRequest(BaseModel):
    """Запрос на отправку подарков"""

    reciver: str
    gift_ids: str  # Comma-separated list of gift IDs


__all__ = [
    "AccountCreateRequest",
    "AccountResponse",
    "ApproveAuthRequest",
    "ApproveRequest",
    "NFTResponse",
    "SelectChannelResponse",
    "SendGiftsRequest",
]
