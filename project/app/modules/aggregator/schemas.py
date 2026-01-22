"""Aggregator модуль - Schemas"""

from pydantic import BaseModel, Field, field_validator


class AggregatorFilter(BaseModel):
    """Фильтр для агрегатора"""

    name: str | None = None
    model: str = "All"
    symbol: str = "All"
    backdrop: str = "All"
    number: int | None = Field(default=None, ge=1)
    from_price: float | None = Field(default=None, ge=0)
    to_price: float | None = Field(default=None, ge=0)
    market: list[str] | None = None
    receiver: int | None = None

    @field_validator("market", mode="before")
    @classmethod
    def filter_empty_markets(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        filtered = [item.strip() for item in v if item and item.strip()]
        return filtered if filtered else None


class AggregatorAttribute(BaseModel):
    value: str | None = None
    rarity: str | None = None


class AggregatorAttributes(BaseModel):
    model: AggregatorAttribute | None = None
    symbol: AggregatorAttribute | None = None
    backdrop: AggregatorAttribute | None = None


class AggregatorOptions(BaseModel):
    payload: str | None = None
    receiver: int | None = None
    contract: str | None = None


class AggregatorItem(BaseModel):
    provider: str
    price: float | int | None = None
    title: str | None = None
    number: int | None = None
    giftId: str | None = None
    slug: str | None = None
    link: str | None = None
    photo_url: str | None = None
    webapp_url: str | None = None
    attributes: AggregatorAttributes | None = None
    options: AggregatorOptions | None = None

    @field_validator("giftId", mode="before")
    @classmethod
    def coerce_gift_id(cls, v: str | int | float | None) -> str | None:
        if v is None:
            return None
        return str(v)


class AggregatorResponse(BaseModel):
    total: int = 0
    items: list[AggregatorItem] = []
