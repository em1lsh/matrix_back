from typing import Generic, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator


# Базовый класс для пагинации
class PaginationRequest(BaseModel):
    """Базовая модель для пагинации с limit/offset"""

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Количество элементов на странице (1-100)",
        examples=[20, 50, 100],
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Смещение от начала списка",
        examples=[0, 20, 40],
    )


# Базовый класс для пагинации с page/count (для обратной совместимости)
class PagePaginationRequest(BaseModel):
    """Базовая модель для пагинации с page/count"""

    page: int = Field(
        default=0,
        ge=0,
        description="Номер страницы (начиная с 0)",
        examples=[0, 1, 2],
    )
    count: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Количество элементов на странице (1-100)",
        examples=[20, 50, 100],
    )


# Generic тип для пагинированных ответов
T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Обёртка для пагинированных ответов"""

    items: list[T] = Field(description="Список элементов")
    total: int = Field(ge=0, description="Общее количество элементов")
    limit: int = Field(ge=1, description="Лимит элементов на странице")
    offset: int = Field(ge=0, description="Смещение")
    has_more: bool = Field(description="Есть ли ещё элементы")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "limit": 20,
                "offset": 0,
                "has_more": True,
            }
        }


class GiftResponse(BaseModel):
    """Модель подарка (NFT) в Telegram"""

    id: str | None = Field(None, description="ID подарка (строка для избежания потери точности в JS)")

    @field_validator("id", mode="before")
    @classmethod
    def convert_id_to_string(cls, v):
        """Конвертирует id в строку для избежания потери точности в JavaScript"""
        if v is not None:
            return str(v)
        return v
    image: str | None = Field(None, description="URL изображения (webp)")
    animation: str | None = Field(None, description="URL анимации (tgs)")
    num: int | None = Field(None, ge=1, description="Номер подарка")

    title: str | None = Field(None, min_length=1, max_length=255, description="Название подарка")
    model_name: str | None = Field(None, min_length=1, max_length=255, description="Название модели")
    pattern_name: str | None = Field(None, min_length=1, max_length=255, description="Название паттерна")
    backdrop_name: str | None = Field(None, min_length=1, max_length=255, description="Название фона")

    model_rarity: float | None = Field(None, ge=0, description="Редкость модели (в процентах)")
    pattern_rarity: float | None = Field(None, ge=0, description="Редкость паттерна (в процентах)")
    backdrop_rarity: float | None = Field(None, ge=0, description="Редкость фона (в процентах)")

    center_color: str | None = Field(None, description="Цвет центра (hex)")
    edge_color: str | None = Field(None, description="Цвет края (hex)")
    pattern_color: str | None = Field(None, description="Цвет паттерна (hex)")
    text_color: str | None = Field(None, description="Цвет текста (hex)")

    @model_validator(mode="before")
    @classmethod
    def set_animation_from_image(cls, data):
        """Сохраняет оригинальный .tgs URL в animation перед конвертацией image в webp"""
        if isinstance(data, dict):
            image = data.get("image")
            if image and isinstance(image, str) and ".tgs" in image:
                # Если animation не задан, берём оригинальный image (tgs)
                if not data.get("animation"):
                    data["animation"] = image
        else:
            # Для ORM объектов (from_attributes=True)
            image = getattr(data, "image", None)
            if image and isinstance(image, str) and ".tgs" in image:
                # Создаём dict для модификации
                return {
                    "id": getattr(data, "id", None),
                    "image": image.replace(".tgs", ".webp"),
                    "animation": image,
                    "num": getattr(data, "num", None),
                    "title": getattr(data, "title", None),
                    "model_name": getattr(data, "model_name", None),
                    "pattern_name": getattr(data, "pattern_name", None),
                    "backdrop_name": getattr(data, "backdrop_name", None),
                    "model_rarity": getattr(data, "model_rarity", None),
                    "pattern_rarity": getattr(data, "pattern_rarity", None),
                    "backdrop_rarity": getattr(data, "backdrop_rarity", None),
                    "center_color": getattr(data, "center_color", None),
                    "edge_color": getattr(data, "edge_color", None),
                    "pattern_color": getattr(data, "pattern_color", None),
                    "text_color": getattr(data, "text_color", None),
                }
        return data

    @field_validator("image", mode="before")
    @classmethod
    def convert_tgs_to_webp(cls, v):
        """Конвертирует .tgs URL в .webp для статичного изображения"""
        if v and isinstance(v, str) and ".tgs" in v:
            return v.replace(".tgs", ".webp")
        return v

    class Config:
        from_attributes = True
