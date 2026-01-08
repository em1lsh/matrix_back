"""Buy Orders модуль - Schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.buy_orders.constants import BuyOrderStatusEnum


class CreateBuyOrderRequest(BaseModel):
    """Запрос на создание ордера."""

    title: str = Field(..., min_length=1, max_length=255)
    price_ton: float = Field(..., gt=0)
    quantity: int = Field(default=1, ge=1)
    model_name: str | None = Field(default=None, max_length=255)
    backdrop_name: str | None = Field(default=None, max_length=255)
    pattern_name: str | None = Field(default=None, max_length=255)


class BuyOrderResponse(BaseModel):
    """Ответ по ордеру."""

    id: int
    status: str
    title: str
    model_name: str | None = None
    pattern_name: str | None = None
    backdrop_name: str | None = None
    price_ton: float
    quantity_total: int
    quantity_remaining: int
    created_at: str


class BuyOrdersFilter(BaseModel):
    """Фильтр списка ордеров."""

    sort: str = "price/asc"
    titles: list[str] | None = None
    models: list[str] | None = None
    patterns: list[str] | None = None
    backdrops: list[str] | None = None
    price_min: float | None = Field(default=None, ge=0)
    price_max: float | None = Field(default=None, ge=0)
    status: BuyOrderStatusEnum | None = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)

    @field_validator("titles", "models", "patterns", "backdrops", mode="before")
    @classmethod
    def strip_empty(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [item.strip() for item in value if item and item.strip()]
        return cleaned or None

    @model_validator(mode="after")
    def validate_prices(self) -> "BuyOrdersFilter":
        if self.price_min is not None and self.price_max is not None and self.price_min > self.price_max:
            raise ValueError("price_min cannot be greater than price_max")
        return self


class BuyOrdersListResponse(BaseModel):
    """Ответ списка ордеров."""

    items: list[BuyOrderResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class SellToOrderRequest(BaseModel):
    """Запрос на продажу NFT в ордер."""

    nft_id: int | None = Field(default=None, ge=1)


class SellToOrderResponse(BaseModel):
    """Ответ продажи в ордер."""

    success: bool
    order_id: int
    nft_id: int
    deal_id: int
    price_ton: float
    commission_ton: float
    seller_amount_ton: float
