"""NFT модуль - Pydantic схемы"""

import typing
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.api.schemas.base import GiftResponse, PagePaginationRequest, PaginatedResponse


class MyNFTFilter(PagePaginationRequest):
    """Фильтр для поиска своих NFT"""

    sort: typing.Literal[
        "created_at/asc",
        "created_at/desc",
        "price/asc",
        "price/desc",
        "num/asc",
        "num/desc",
        "model_rarity/asc",
        "model_rarity/desc",
    ] = Field(default="created_at/desc", description="Сортировка результатов")

    titles: list[str] | None = Field(None, max_length=50, description="Фильтр по названиям коллекций (макс. 50)")
    models: list[str] | None = Field(None, max_length=50, description="Фильтр по моделям (макс. 50)")
    patterns: list[str] | None = Field(None, max_length=50, description="Фильтр по паттернам (макс. 50)")
    backdrops: list[str] | None = Field(None, max_length=50, description="Фильтр по фонам (макс. 50)")

    num: int | None = Field(None, ge=1, description="Номер NFT")
    num_min: int | None = Field(None, ge=1, description="Минимальный номер NFT")
    num_max: int | None = Field(None, ge=1, description="Максимальный номер NFT")

    on_sale: bool | None = Field(None, description="Фильтр по статусу продажи (True - на продаже, False - не на продаже)")

    @field_validator("titles", "models", "patterns", "backdrops", mode="before")
    @classmethod
    def filter_empty_strings(cls, v: list[str] | None) -> list[str] | None:
        """Удаляем пустые строки из списков фильтров, возвращаем None если список пуст"""
        if v is None:
            return None
        filtered = [item.strip() for item in v if item and item.strip()]
        return filtered if filtered else None

    @field_validator("titles", "models", "patterns", "backdrops")
    @classmethod
    def validate_list_length(cls, v: list[str] | None) -> list[str] | None:
        """Валидация длины списков фильтров"""
        if v and len(v) > 50:
            raise ValueError("Максимум 50 элементов в фильтре")
        return v

    @model_validator(mode="after")
    def validate_ranges(self) -> "MyNFTFilter":
        """Валидация диапазонов номеров"""
        if self.num_min is not None and self.num_max is not None:
            if self.num_min > self.num_max:
                raise ValueError("num_min не может быть больше num_max")
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "page": 0,
                "count": 20,
                "sort": "created_at/desc",
                "titles": ["Delicious Cake"],
                "models": ["Model A"],
                "patterns": ["Pattern X"],
                "backdrops": ["Backdrop Y"],
                "num": None,
                "num_min": 1,
                "num_max": 1000,
                "on_sale": True,
            }
        }


class NFTResponse(BaseModel):
    """NFT ответ"""

    id: int = Field(description="ID NFT")
    gift: GiftResponse = Field(description="Подарок")
    price: float | None = Field(None, ge=0, description="Цена в TON")
    is_promoted: bool = Field(False, description="Активно ли продвижение NFT")
    promoted_ends_at: datetime | None = Field(
        None, description="Дата окончания активного продвижения (если есть)"
    )
    active_bundle_id: int | None = Field(None, description="ID активного бандла (если NFT в бандле)")
    created_at: datetime = Field(description="Дата создания")

    class Config:
        from_attributes = True


class SetPriceRequest(BaseModel):
    """Установка цены NFT"""

    nft_id: int = Field(gt=0, description="ID NFT")
    price_ton: float | None = Field(None, ge=0, le=100000, description="Цена в TON (None для снятия)")

    @field_validator("price_ton")
    @classmethod
    def validate_price(cls, v: float | None) -> float | None:
        if v is not None:
            if v < 0.1:
                raise ValueError("Минимальная цена 0.1 TON")
            return round(v, 2)
        return v

    class Config:
        json_schema_extra = {"example": {"nft_id": 123, "price_ton": 50.0}}


class BuyRequest(BaseModel):
    """Покупка NFT"""

    nft_id: int = Field(gt=0, description="ID NFT")

    class Config:
        json_schema_extra = {"example": {"nft_id": 123}}


class ReturnRequest(BaseModel):
    """Возврат NFT в Telegram"""

    nft_id: int = Field(gt=0, description="ID NFT")

    class Config:
        json_schema_extra = {"example": {"nft_id": 123}}


class NFTDealsFilter(BaseModel):
    """Фильтр сделок"""

    gift_id: int = Field(gt=0, description="ID подарка")
    limit: int = Field(default=20, ge=1, le=100, description="Количество элементов (1-100)")
    offset: int = Field(default=0, ge=0, description="Смещение от начала списка")

    class Config:
        json_schema_extra = {"example": {"gift_id": 456, "limit": 20, "offset": 0}}


class NFTDealResponse(BaseModel):
    """Сделка NFT"""

    id: int
    price: float
    created_at: datetime
    gift: GiftResponse

    class Config:
        from_attributes = True


class NFTDealsList(BaseModel):
    """Список сделок с пагинацией"""

    deals: list[NFTDealResponse] = Field(default=[], description="Список сделок")
    total: int = Field(ge=0, description="Общее количество сделок")
    limit: int = Field(ge=1, description="Лимит элементов на странице")
    offset: int = Field(ge=0, description="Смещение")
    has_more: bool = Field(description="Есть ли ещё элементы")

    class Config:
        json_schema_extra = {"example": {"deals": [], "total": 50, "limit": 20, "offset": 0, "has_more": True}}


class NFTListResponse(PaginatedResponse[NFTResponse]):
    """Список NFT с пагинацией"""

    pass
