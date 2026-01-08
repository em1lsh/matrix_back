import datetime

from pydantic import BaseModel, Field, field_validator

from .base import GiftResponse


class NFTResponse(BaseModel):
    """Информация о NFT"""

    id: int = Field(description="ID NFT")
    gift: GiftResponse = Field(description="Информация о подарке")
    price: float | None = Field(None, ge=0, description="Цена в TON (если выставлен на продажу)")
    created_at: datetime.datetime = Field(description="Дата создания")

    class Config:
        from_attributes = True


class NFTDealResponse(BaseModel):
    """Информация о сделке с NFT"""

    id: int = Field(description="ID сделки")
    price: float = Field(ge=0, description="Цена сделки в TON")
    created_at: datetime.datetime = Field(description="Дата сделки")
    gift: GiftResponse = Field(description="Информация о подарке")

    class Config:
        from_attributes = True


class NFTOfferResponse(BaseModel):
    """Предложение на NFT"""

    id: int = Field(description="ID предложения")
    nft: NFTResponse = Field(description="NFT")
    price: float = Field(ge=0, description="Предложенная цена в TON")
    reciprocal_price: float | None = Field(None, ge=0, description="Встречная цена в TON")
    updated: datetime.datetime = Field(description="Дата обновления")
    is_sended: bool = Field(description="True если оффер отправлен пользователем")

    class Config:
        from_attributes = True


class NFTOffersList(BaseModel):
    """Список предложений на NFT"""

    offers: list[NFTOfferResponse] = Field(default=[], description="Список предложений")
    total: int = Field(ge=0, description="Общее количество предложений")
    limit: int = Field(ge=1, description="Лимит элементов на странице")
    offset: int = Field(ge=0, description="Смещение")
    has_more: bool = Field(description="Есть ли ещё предложения")

    class Config:
        json_schema_extra = {
            "example": {
                "offers": [],
                "total": 10,
                "limit": 20,
                "offset": 0,
                "has_more": False,
            }
        }


class NFTPreSale(BaseModel):
    """NFT на предпродаже"""

    id: int = Field(description="ID предпродажи")
    gift: GiftResponse = Field(description="Информация о подарке")
    price: int | None = Field(None, ge=0, description="Цена в nanotons")

    class Config:
        from_attributes = True


class SetNFTPriceRequest(BaseModel):
    """Запрос на установку цены NFT"""

    nft_id: int = Field(gt=0, description="ID NFT")
    price_ton: float | None = Field(None, ge=0, le=100000, description="Цена в TON (None для снятия с продажи)")

    @field_validator("price_ton")
    @classmethod
    def validate_price(cls, v: float | None) -> float | None:
        """Валидация цены"""
        if v is not None:
            if v < 0.1:
                raise ValueError("Минимальная цена 0.1 TON")
            return round(v, 2)
        return v

    class Config:
        json_schema_extra = {"example": {"nft_id": 123, "price_ton": 50.0}}


class BuyNFTRequest(BaseModel):
    """Запрос на покупку NFT"""

    nft_id: int = Field(gt=0, description="ID NFT для покупки")

    class Config:
        json_schema_extra = {"example": {"nft_id": 123}}


class ReturnNFTRequest(BaseModel):
    """Запрос на возврат NFT в Telegram"""

    nft_id: int = Field(gt=0, description="ID NFT для возврата")

    class Config:
        json_schema_extra = {"example": {"nft_id": 123}}


class NFTDealsList(BaseModel):
    """Список сделок с NFT"""

    deals: list[NFTDealResponse] = Field(default=[], description="Список сделок")
    total: int = Field(ge=0, description="Общее количество сделок")
    limit: int = Field(ge=1, description="Лимит элементов на странице")
    offset: int = Field(ge=0, description="Смещение")
    has_more: bool = Field(description="Есть ли ещё элементы")

    class Config:
        json_schema_extra = {"example": {"deals": [], "total": 50, "limit": 20, "offset": 0, "has_more": True}}


class NFTDealsFilter(BaseModel):
    """Фильтр для получения сделок по NFT"""

    gift_id: int = Field(gt=0, description="ID подарка")
    limit: int = Field(default=20, ge=1, le=100, description="Количество элементов (1-100)")
    offset: int = Field(default=0, ge=0, description="Смещение от начала списка")

    class Config:
        json_schema_extra = {"example": {"gift_id": 456, "limit": 20, "offset": 0}}
