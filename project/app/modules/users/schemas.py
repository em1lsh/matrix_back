"""Users модуль - Pydantic схемы"""

# Импортируем из существующих схем
from app.api.schemas.user import (
    AuthTokenResponse,
    PayResponse,
    TopupResponse,
    TopupsList,
    TransactionResponse,
    TransactionsList,
    UserResponse,
    WithdrawRequest,
    WithdrawResponse,
    WithdrawsList,
)

# Импортируем NFT deals схемы для sells/buys
from app.modules.nft.schemas import NFTDealResponse, NFTDealsList


__all__ = [
    "AuthTokenResponse",
    "NFTDealResponse",
    "NFTDealsList",
    "PayResponse",
    "TopupResponse",
    "TopupsList",
    "TransactionResponse",
    "TransactionsList",
    "UserResponse",
    "WithdrawRequest",
    "WithdrawResponse",
    "WithdrawsList",
]
