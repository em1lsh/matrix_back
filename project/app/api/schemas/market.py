import datetime
import typing

from pydantic import BaseModel, Field, field_validator, model_validator

from .base import GiftResponse, PagePaginationRequest, PaginatedResponse


class MarketResponse(BaseModel):
    """Информация о маркетплейсе"""

    id: int = Field(description="ID маркетплейса")
    title: str = Field(min_length=1, max_length=255, description="Название маркетплейса")
    logo: str | None = Field(None, description="URL логотипа")

    class Config:
        from_attributes = True


class SalingFilter(PagePaginationRequest):
    """Фильтр для поиска NFT на маркете"""

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
    price_min: float | None = Field(None, ge=0, description="Минимальная цена в TON")
    price_max: float | None = Field(None, ge=0, description="Максимальная цена в TON")

    @field_validator("titles", "models", "patterns", "backdrops", mode="before")
    @classmethod
    def filter_empty_strings(cls, v: list[str] | None) -> list[str] | None:
        """Удаляем пустые строки из списков фильтров, возвращаем None если список пуст"""
        if v is None:
            return None
        # Фильтруем пустые строки и строки только из пробелов
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
    def validate_price_range(self) -> "SalingFilter":
        """Валидация диапазона цен"""
        if self.price_min is not None and self.price_max is not None and self.price_min > self.price_max:
            raise ValueError("price_min не может быть больше price_max")
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "page": 0,
                "count": 20,
                "sort": "price/asc",
                "titles": ["Delicious Cake", "Green Star"],
                "price_min": 10.0,
                "price_max": 100.0,
            }
        }


class SalingResponse(BaseModel):
    """NFT на продаже"""

    id: int | str = Field(description="ID NFT")
    price: float = Field(ge=0, description="Цена в nanotons")
    gift: GiftResponse = Field(description="Информация о подарке")
    market: MarketResponse | None = Field(None, description="Маркетплейс")

    class Config:
        from_attributes = True


class SalingsListResponse(PaginatedResponse[SalingResponse]):
    """Пагинированный список NFT на продаже"""

    pass


class CollectionFilterResponse(BaseModel):
    """Фильтр по коллекции"""

    collection: str = Field(min_length=1, max_length=255, description="Название коллекции")
    image: str = Field(description="URL изображения коллекции")

    class Config:
        json_schema_extra = {
            "example": {
                "collection": "Delicious Cake",
                "image": "https://fragment.com/file/gifts/delicious-cake/thumb.webp",
            }
        }


class ModelFilterResponse(BaseModel):
    """Фильтр по модели"""

    model: str = Field(min_length=1, max_length=255, description="Название модели")
    image: str = Field(description="URL изображения модели")


class BackdropFilterResponse(BaseModel):
    """Фильтр по фону"""

    backdrop: str = Field(min_length=1, max_length=255, description="Название фона")
    center_color: int = Field(description="Цвет центра")
    edge_color: int = Field(description="Цвет края")


class PatternFilterResponse(BaseModel):
    """Фильтр по паттерну"""

    pattern: str = Field(min_length=1, max_length=255, description="Название паттерна")
    image: str = Field(description="URL изображения паттерна")


class MarketFloorResponse(BaseModel):
    """Изменение цены коллекции / модели на маркете"""

    price_nanotons: int = Field(ge=0, description="Цена в nanotons")
    price_dollars: float = Field(ge=0, description="Цена в долларах")
    price_rubles: float = Field(ge=0, description="Цена в рублях")
    created_at: datetime.datetime = Field(description="Дата записи")

    class Config:
        from_attributes = True


class MarketChartResponse(BaseModel):
    """История изменения цены на маркете для модели/коллекции"""

    name: str = Field(min_length=1, max_length=255, description="Название модели/коллекции")
    floors: list[MarketFloorResponse] = Field(default=[], description="История цен")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Delicious Cake",
                "floors": [
                    {
                        "price_nanotons": 10000000000,
                        "price_dollars": 50,
                        "price_rubles": 5000,
                        "created_at": "2025-12-06T12:00:00",
                    }
                ],
            }
        }


class MarketFloorFilter(BaseModel):
    """Фильтр для получения истории изменения цены маркета/коллекции"""

    name: str = Field(min_length=1, max_length=255, description="Название модели/коллекции")
    time_range: typing.Literal["1", "7", "30"] = Field(default="1", description="Период в днях (1, 7 или 30)")

    class Config:
        json_schema_extra = {"example": {"name": "Delicious Cake", "time_range": "7"}}
