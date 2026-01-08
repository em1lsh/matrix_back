"""
Типизация для функционала аукционов
"""

import datetime
import typing

from pydantic import BaseModel, Field, field_validator, model_validator

from .base import GiftResponse, PagePaginationRequest
from .nft import NFTResponse


class AuctionFilter(PagePaginationRequest):
    """Фильтр для поиска аукционов"""

    sort: typing.Literal[
        "created_at/asc",
        "created_at/desc",
        "price/asc",
        "price/desc",
        "num/asc",
        "num/desc",
        "model_rarity/asc",
        "model_rarity/desc",
    ] = Field(default="price/asc", description="Сортировка результатов")

    titles: list[str] | None = Field(None, max_length=50, description="Фильтр по названиям коллекций (макс. 50)")
    models: list[str] | None = Field(None, max_length=50, description="Фильтр по моделям (макс. 50)")
    patterns: list[str] | None = Field(None, max_length=50, description="Фильтр по паттернам (макс. 50)")
    backdrops: list[str] | None = Field(None, max_length=50, description="Фильтр по фонам (макс. 50)")

    num: int | None = Field(None, ge=1, description="Номер NFT")
    num_min: int | None = Field(None, ge=1, description="Минимальный номер NFT")
    num_max: int | None = Field(None, ge=1, description="Максимальный номер NFT")
    
    price_min: float | None = Field(None, ge=0, description="Минимальная цена в TON")
    price_max: float | None = Field(None, ge=0, description="Максимальная цена в TON")

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
    def validate_ranges(self) -> "AuctionFilter":
        """Валидация диапазонов цен и номеров"""
        if self.price_min is not None and self.price_max is not None:
            if self.price_min > self.price_max:
                raise ValueError("price_min не может быть больше price_max")
        if self.num_min is not None and self.num_max is not None:
            if self.num_min > self.num_max:
                raise ValueError("num_min не может быть больше num_max")
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "page": 0,
                "count": 20,
                "sort": "price/asc",
                "titles": ["Delicious Cake"],
                "price_min": 10.0,
                "price_max": 100.0,
            }
        }


class AuctionResponse(BaseModel):
    """Объект аукциона"""

    id: int = Field(description="ID аукциона")
    nft: NFTResponse = Field(description="NFT на аукционе")
    start_bid: float = Field(ge=0, description="Начальная ставка в TON")
    last_bid: float | None = Field(None, description="Последняя ставка в TON")
    expired_at: datetime.datetime = Field(description="Дата окончания аукциона")
    created_at: datetime.datetime = Field(description="Дата создания аукциона")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "nft": {"id": 123, "gift": {}, "price": None, "created_at": "2025-12-06T12:00:00"},
                "start_bid": 10.5,
                "last_bid": 15000000000,
                "expired_at": "2025-12-07T12:00:00",
                "created_at": "2025-12-06T12:00:00",
            }
        }


class NewAuctionRequest(BaseModel):
    """Запрос на создание нового аукциона"""

    nft_id: int = Field(gt=0, description="ID NFT для аукциона", examples=[123, 456])
    step_bid: float = Field(
        default=10,
        gt=0,
        le=100,
        description="Шаг ставки в процентах от текущей ставки",
        examples=[5.0, 10.0, 25.0],
    )
    start_bid_ton: float = Field(
        gt=0,
        le=10000,
        description="Начальная ставка в TON",
        examples=[10.0, 50.0, 100.0],
    )
    term_hours: int = Field(
        default=1,
        ge=1,
        le=168,
        description="Срок аукциона в часах (1-168, т.е. до 7 дней)",
        examples=[1, 24, 72, 168],
    )

    @field_validator("start_bid_ton")
    @classmethod
    def validate_start_bid(cls, v: float) -> float:
        """Валидация начальной ставки"""
        if v < 0.1:
            raise ValueError("Минимальная начальная ставка 0.1 TON")
        if v > 10000:
            raise ValueError("Максимальная начальная ставка 10000 TON")
        return round(v, 2)

    @field_validator("step_bid")
    @classmethod
    def validate_step_bid(cls, v: float) -> float:
        """Валидация шага ставки (в процентах)"""
        if v < 1:
            raise ValueError("Минимальный шаг ставки 1%")
        if v > 100:
            raise ValueError("Максимальный шаг ставки 100%")
        return round(v, 2)

    class Config:
        json_schema_extra = {
            "example": {
                "nft_id": 123,
                "step_bid": 5.0,
                "start_bid_ton": 50.0,
                "term_hours": 24,
            }
        }


class NewBidRequest(BaseModel):
    """Запрос на создание новой ставки на аукцион"""

    auction_id: int = Field(gt=0, description="ID аукциона", examples=[1, 2, 3])
    bid_ton: float = Field(
        gt=0,
        le=100000,
        description="Размер ставки в TON",
        examples=[15.0, 25.0, 50.0],
    )

    @field_validator("bid_ton")
    @classmethod
    def validate_bid(cls, v: float) -> float:
        """Валидация ставки"""
        if v < 0.1:
            raise ValueError("Минимальная ставка 0.1 TON")
        return round(v, 2)

    class Config:
        json_schema_extra = {
            "example": {
                "auction_id": 1,
                "bid_ton": 55.0,
            }
        }


class AuctionDealResponse(BaseModel):
    """Объект сделки аукциона"""

    id: int = Field(description="ID сделки")
    gift: GiftResponse = Field(description="Подарок")
    is_buy: bool = Field(default=False, description="Покупка или продажа")
    price: float = Field(ge=0, description="Цена в TON")
    created_at: datetime.datetime = Field(description="Дата сделки")

    class Config:
        from_attributes = True


class AuctionListResponse(BaseModel):
    """Пагинированный список аукционов"""

    auctions: list[AuctionResponse] = Field(description="Список аукционов")
    total: int = Field(ge=0, description="Общее количество аукционов")
    limit: int = Field(ge=1, description="Лимит элементов на странице")
    offset: int = Field(ge=0, description="Смещение")
    has_more: bool = Field(description="Есть ли ещё элементы")

    class Config:
        json_schema_extra = {
            "example": {
                "auctions": [],
                "total": 0,
                "limit": 20,
                "offset": 0,
                "has_more": False,
            }
        }
