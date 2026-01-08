from pydantic import BaseModel, Field, field_validator

from .base import GiftResponse, PagePaginationRequest
from .nft import NFTResponse


class TradeRequirementResponse(BaseModel):
    """Требование для трейда"""

    collection: str = Field(min_length=1, max_length=255, description="Название коллекции")
    backdrop: str | None = Field(None, min_length=1, max_length=255, description="Название фона")

    class Config:
        from_attributes = True


class TradeResponse(BaseModel):
    """Трейд общедоступный для ленты трейдов"""

    id: int = Field(description="ID трейда")
    nfts: list[NFTResponse] = Field(description="NFT для обмена")
    requirements: list[TradeRequirementResponse] = Field(description="Требования к обмену")

    class Config:
        from_attributes = True


class MyTradeResponse(TradeResponse):
    """Свой трейд"""

    receiver_id: int | None = Field(None, description="ID получателя (если приватный трейд)")


class TradeRequest(BaseModel):
    """Форма нового трейда"""

    receiver_id: int | None = Field(None, description="ID получателя для приватного трейда")
    nft_ids: list[int] = Field(min_length=1, max_length=50, description="ID NFT для обмена (1-50)")
    requirements: list[TradeRequirementResponse] = Field(
        min_length=1, max_length=20, description="Требования к обмену (1-20)"
    )

    @field_validator("nft_ids")
    @classmethod
    def validate_nft_ids(cls, v: list[int]) -> list[int]:
        """Валидация списка NFT"""
        if not v:
            raise ValueError("Необходимо указать хотя бы один NFT")
        if len(v) > 50:
            raise ValueError("Максимум 50 NFT в одном трейде")
        if len(v) != len(set(v)):
            raise ValueError("NFT не должны повторяться")
        return v

    @field_validator("requirements")
    @classmethod
    def validate_requirements(cls, v: list[TradeRequirementResponse]) -> list[TradeRequirementResponse]:
        """Валидация требований"""
        if not v:
            raise ValueError("Необходимо указать хотя бы одно требование")
        if len(v) > 20:
            raise ValueError("Максимум 20 требований в одном трейде")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "receiver_id": None,
                "nft_ids": [123, 456, 789],
                "requirements": [{"collection": "Delicious Cake", "backdrop": "Blue"}],
            }
        }


class TradeProposalRequest(BaseModel):
    """Предложение на трейд (запрос)"""

    trade_id: int = Field(gt=0, description="ID трейда")
    nft_ids: list[int] = Field(min_length=1, max_length=50, description="ID NFT для предложения (1-50)")

    @field_validator("nft_ids")
    @classmethod
    def validate_nft_ids(cls, v: list[int]) -> list[int]:
        """Валидация списка NFT"""
        if not v:
            raise ValueError("Необходимо указать хотя бы один NFT")
        if len(v) > 50:
            raise ValueError("Максимум 50 NFT в одном предложении")
        if len(v) != len(set(v)):
            raise ValueError("NFT не должны повторяться")
        return v

    class Config:
        json_schema_extra = {"example": {"trade_id": 1, "nft_ids": [111, 222, 333]}}


class TradeProposalResponse(BaseModel):
    """Предложение на трейд (ответ)"""

    id: int = Field(description="ID предложения")
    trade: TradeResponse = Field(description="Трейд")
    nfts: list[NFTResponse] = Field(description="NFT в предложении")

    class Config:
        from_attributes = True


class MyTradeProposalResponse(BaseModel):
    """Предложения на мои трейды"""

    id: int = Field(description="ID предложения")
    trade: MyTradeResponse = Field(description="Мой трейд")
    nfts: list[NFTResponse] = Field(description="NFT в предложении")

    class Config:
        from_attributes = True


class TradeDealResponse(BaseModel):
    """Сделка по трейду в истории"""

    sent: list[GiftResponse] = Field(description="Отправленные подарки")
    received: list[GiftResponse] = Field(description="Полученные подарки")

    class Config:
        from_attributes = True


class TradeHistoryResponse(BaseModel):
    """История трейдов"""

    buys: list[TradeDealResponse] = Field(default=[], description="Покупки")
    sells: list[TradeDealResponse] = Field(default=[], description="Продажи")


class TradeFilterSendRequirement(BaseModel):
    """Фильтр по отправляемым NFT"""

    collection: str | None = Field(None, min_length=1, max_length=255, description="Коллекция")
    model: str | None = Field(None, min_length=1, max_length=255, description="Модель")
    backdrop: str | None = Field(None, min_length=1, max_length=255, description="Фон")


class TradeFilterGiveRequirement(BaseModel):
    """Фильтр по получаемым NFT"""

    collection: str | None = Field(None, min_length=1, max_length=255, description="Коллекция")
    backdrop: str | None = Field(None, min_length=1, max_length=255, description="Фон")


class TradeFilter(PagePaginationRequest):
    """Фильтр для ленты трейдов"""

    sent_requirements: list[TradeFilterSendRequirement] | None = Field(
        None, max_length=20, description="Требования к отправляемым NFT"
    )
    received_requirements: list[TradeFilterGiveRequirement] | None = Field(
        None, max_length=20, description="Требования к получаемым NFT"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "page": 0,
                "count": 20,
                "sent_requirements": [{"collection": "Delicious Cake", "model": "Cake"}],
                "received_requirements": [{"collection": "Green Star", "backdrop": "Blue"}],
            }
        }
