from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.api.schemas.base import GiftResponse


class BundleFilter(BaseModel):
    titles: list[str] | None = None
    models: list[str] | None = None
    patterns: list[str] | None = None
    backdrops: list[str] | None = None
    num: int | None = Field(None, gt=0)
    num_min: int | None = Field(None, gt=0)
    num_max: int | None = Field(None, gt=0)
    price_min: float | None = Field(None, ge=0)
    price_max: float | None = Field(None, ge=0)
    sort: str | None = Field(None, description="Sort format: field/direction (e.g. price/asc, created_at/desc)")
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)

    @field_validator("sort")
    @classmethod
    def validate_sort(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if "/" not in v:
            raise ValueError("Sort format must be 'field/direction' (e.g. price/asc)")
        field, direction = v.split("/", 1)
        valid_fields = {"price", "created_at", "num", "model_rarity", "pattern_rarity", "backdrop_rarity"}
        valid_directions = {"asc", "desc"}
        if field not in valid_fields:
            raise ValueError(f"Invalid sort field. Valid: {valid_fields}")
        if direction not in valid_directions:
            raise ValueError(f"Invalid sort direction. Valid: {valid_directions}")
        return v

    @field_validator("limit")
    @classmethod
    def clamp_limit(cls, v: int) -> int:
        return min(v, 100)


class CreateBundleRequest(BaseModel):
    nft_ids: list[int] = Field(..., min_length=2, description="List of NFT IDs to include in bundle")
    price_ton: float = Field(..., ge=0.1, description="Bundle price in TON")

    @field_validator("price_ton")
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v < 0.1:
            raise ValueError("Минимальная цена 0.1 TON")
        return round(v, 2)

    @field_validator("nft_ids")
    @classmethod
    def ensure_unique_ids(cls, v: list[int]) -> list[int]:
        if len(set(v)) != len(v):
            raise ValueError("NFT IDs must be unique")
        return v


class CancelBundleRequest(BaseModel):
    bundle_id: int = Field(gt=0, description="Bundle ID")


class BuyBundleRequest(BaseModel):
    bundle_id: int = Field(gt=0, description="Bundle ID to buy")


class BundleOfferRequest(BaseModel):
    bundle_id: int = Field(gt=0, description="Bundle ID")
    price_ton: float = Field(..., ge=0.1, description="Offer price in TON")

    @field_validator("price_ton")
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v < 0.1:
            raise ValueError("Минимальная цена 0.1 TON")
        return round(v, 2)


class BundleItemResponse(BaseModel):
    nft_id: int
    gift: GiftResponse

    class Config:
        from_attributes = True


class BundleResponse(BaseModel):
    id: int
    seller_id: int
    price: float
    status: str
    created_at: datetime
    items: list[BundleItemResponse]

    class Config:
        from_attributes = True


class BundlesListResponse(BaseModel):
    items: list[BundleResponse]
    total: int
    limit: int
    offset: int
    has_more: bool