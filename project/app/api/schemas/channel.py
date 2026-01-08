import datetime
import re

from pydantic import BaseModel, Field, field_validator

from .base import GiftResponse


class SelectChannelResponse(BaseModel):
    """Краткая информация о канале для выбора"""

    id: int = Field(description="ID канала")
    title: str = Field(min_length=1, max_length=255, description="Название канала")
    username: str | None = Field(None, min_length=1, max_length=255, description="Username канала")

    class Config:
        from_attributes = True


class ChannelGiftResponse(BaseModel):
    """Подарок в канале"""

    id: int = Field(description="ID записи")
    gift_id: int = Field(description="ID подарка")
    gift: GiftResponse = Field(description="Информация о подарке")
    channel_id: int | None = Field(None, description="ID канала")
    quantity: int = Field(ge=0, description="Количество подарков")

    class Config:
        from_attributes = True


class ChannelResponse(BaseModel):
    """Полная информация о канале"""

    id: int = Field(description="ID канала")
    title: str = Field(min_length=1, max_length=255, description="Название канала")
    username: str | None = Field(None, min_length=1, max_length=255, description="Username канала")
    price: float | None = Field(None, ge=0, description="Цена канала в TON")
    channel_gifts: list[ChannelGiftResponse] = Field(default=[], description="Подарки в канале")

    class Config:
        from_attributes = True


class ChannelDealResponse(BaseModel):
    """Сделка по каналу"""

    title: str = Field(min_length=1, max_length=255, description="Название канала")
    username: str | None = Field(None, min_length=1, max_length=255, description="Username канала")
    price: float = Field(ge=0, description="Цена сделки в TON")
    created_at: datetime.datetime = Field(description="Дата сделки")
    deal_gifts: list[ChannelGiftResponse] = Field(default=[], description="Подарки в сделке")

    class Config:
        from_attributes = True


class ChannelCreateRequest(BaseModel):
    """Запрос на добавление канала"""

    channel_username: str = Field(min_length=1, max_length=255, description="Username канала (без @)")
    price_ton: float = Field(gt=0, le=100000, description="Цена канала в TON")

    @field_validator("channel_username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Валидация username канала"""
        # Удаляем @ если есть
        v = v.lstrip("@")

        # Проверяем формат
        if not re.match(r"^[a-zA-Z0-9_]{5,32}$", v):
            raise ValueError("Username должен содержать от 5 до 32 символов (латинские буквы, цифры, подчёркивание)")

        return v

    @field_validator("price_ton")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Валидация цены"""
        if v < 0.1:
            raise ValueError("Минимальная цена 0.1 TON")
        return round(v, 2)

    class Config:
        json_schema_extra = {"example": {"channel_username": "my_channel", "price_ton": 100.0}}
