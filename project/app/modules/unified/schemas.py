"""Unified модуль - Schemas"""

import typing
from pydantic import BaseModel, Field, field_validator, model_validator


class GiftAttributeResponse(BaseModel):
    """Атрибут подарка (model/symbol/backdrop)"""
    value: str | None = None
    rarity: float | None = None


class GiftResponse(BaseModel):
    """Подарок"""
    id: int | None = None
    image: str = ""  # webp версия
    animation: str | None = None  # tgs версия (оригинальная)
    num: int | None = None
    title: str | None = None
    model_name: str | None = None
    pattern_name: str | None = None
    backdrop_name: str | None = None
    model_rarity: float | None = None
    pattern_rarity: float | None = None
    backdrop_rarity: float | None = None
    model: GiftAttributeResponse | None = None
    symbol: GiftAttributeResponse | None = None
    backdrop: GiftAttributeResponse | None = None
    center_color: str = ""
    edge_color: str = ""
    pattern_color: str = ""
    text_color: str = ""

    @model_validator(mode="after")
    def populate_attribute_objects(self) -> "GiftResponse":
        """Заполняем объектные атрибуты на основе плоских полей."""
        if self.model is None and (self.model_name or self.model_rarity is not None):
            self.model = GiftAttributeResponse(value=self.model_name, rarity=self.model_rarity)
        if self.symbol is None and (self.pattern_name or self.pattern_rarity is not None):
            self.symbol = GiftAttributeResponse(value=self.pattern_name, rarity=self.pattern_rarity)
        if self.backdrop is None and (self.backdrop_name or self.backdrop_rarity is not None):
            self.backdrop = GiftAttributeResponse(value=self.backdrop_name, rarity=self.backdrop_rarity)
        return self


class MarketInfo(BaseModel):
    """Информация о маркете"""
    id: str
    title: str
    logo: str | None = None


class SalingItem(BaseModel):
    """Продаваемый подарок"""
    id: str
    price: int  # в nanotons
    gift: GiftResponse
    market: MarketInfo


# Допустимые маркеты
VALID_MARKETS = {"internal", "mrkt", "portals", "tonnel"}


class UnifiedFilter(BaseModel):
    """Фильтр для объединённого списка"""
    sort: typing.Literal[
        "created_at/asc", "created_at/desc",
        "price/asc", "price/desc",
        "num/asc", "num/desc",
        "model_rarity/asc", "model_rarity/desc",
    ] = "price/asc"
    
    titles: list[str] | None = Field(default=None, max_length=50, description="Фильтр по названиям коллекций")
    models: list[str] | None = Field(default=None, max_length=50, description="Фильтр по моделям")
    patterns: list[str] | None = Field(default=None, max_length=50, description="Фильтр по паттернам")
    backdrops: list[str] | None = Field(default=None, max_length=50, description="Фильтр по фонам")
    
    num: int | None = Field(default=None, ge=1, description="Номер NFT")
    num_min: int | None = Field(default=None, ge=1, description="Минимальный номер NFT")
    num_max: int | None = Field(default=None, ge=1, description="Максимальный номер NFT")
    
    price_min: float | None = Field(default=None, ge=0, description="Минимальная цена в TON")
    price_max: float | None = Field(default=None, ge=0, description="Максимальная цена в TON")
    
    offset: int = Field(default=0, ge=0, description="Смещение для пагинации")
    limit: int = Field(default=20, ge=1, le=100, description="Количество элементов (макс. 100)")
    
    # Фильтр по маркетам (если пустой - все маркеты)
    # Доступные: "internal", "mrkt", "portals", "tonnel"
    markets: list[str] | None = Field(default=None, description="Маркеты: internal, mrkt, portals, tonnel")

    model_config = {
        "json_schema_extra": {
            "example": {
                "sort": "price/asc",
                "titles": [],
                "models": [],
                "patterns": [],
                "backdrops": [],
                "num": 0,
                "num_min": 0,
                "num_max": 0,
                "price_min": 0,
                "price_max": 0,
                "offset": 0,
                "limit": 20,
                "markets": []
            }
        }
    }

    @field_validator("titles", "models", "patterns", "backdrops", mode="before")
    @classmethod
    def filter_empty_strings_in_filters(cls, v: list[str] | None) -> list[str] | None:
        """Удаляем пустые строки и пробелы из списков фильтров, возвращаем None если список пуст"""
        if v is None:
            return None
        # Фильтруем пустые строки и строки только из пробелов
        filtered = [item.strip() for item in v if item and item.strip()]
        # Возвращаем None если после фильтрации список пуст
        return filtered if filtered else None

    @field_validator("markets", mode="before")
    @classmethod
    def filter_and_validate_markets(cls, v: list[str] | None) -> list[str] | None:
        """Удаляем пустые строки и валидируем маркеты, возвращаем None если список пуст"""
        if v is None:
            return None
        
        # Фильтруем пустые строки и пробелы
        filtered = [item.strip() for item in v if item and item.strip()]
        
        # Если после фильтрации список пуст, возвращаем None
        if not filtered:
            return None
        
        # Валидация - только допустимые маркеты
        invalid = [m for m in filtered if m not in VALID_MARKETS]
        if invalid:
            raise ValueError(
                f"Недопустимые маркеты: {invalid}. "
                f"Допустимые значения: {', '.join(sorted(VALID_MARKETS))}"
            )
        
        return filtered

    @field_validator("titles", "models", "patterns", "backdrops")
    @classmethod
    def validate_list_length(cls, v: list[str] | None) -> list[str] | None:
        """Валидация длины списков фильтров"""
        if v and len(v) > 50:
            raise ValueError("Максимум 50 элементов в фильтре")
        return v

    @model_validator(mode="after")
    def validate_ranges(self) -> "UnifiedFilter":
        """Валидация диапазонов цен и номеров"""
        # Валидация диапазона цен
        if self.price_min is not None and self.price_max is not None:
            if self.price_min > self.price_max:
                raise ValueError("price_min не может быть больше price_max")
        
        # Валидация диапазона номеров
        if self.num_min is not None and self.num_max is not None:
            if self.num_min > self.num_max:
                raise ValueError("num_min не может быть больше num_max")
        
        return self


class UnifiedResponse(BaseModel):
    """Ответ объединённого списка"""
    items: list[SalingItem] = []
    total: int = 0
