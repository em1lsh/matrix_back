"""Схемы для модуля stars"""

from datetime import datetime
from typing import Optional
import re

from pydantic import BaseModel, Field, field_validator, ConfigDict


class StarsPriceRequest(BaseModel):
    """Запрос цены звёзд"""
    stars_amount: int = Field(..., ge=1, le=1000000, description="Количество звёзд (1-1000000)")


class StarsPriceResponse(BaseModel):
    """Ответ с ценой звёзд"""
    stars_amount: int
    fragment_price_ton: float
    markup_percent: int
    final_price_ton: float
    final_price_nanotons: int
    profit_ton: float


class BuyStarsRequest(BaseModel):
    """Запрос покупки звёзд"""
    recipient_username: str = Field(..., min_length=5, max_length=32, description="Username получателя")
    stars_amount: int = Field(..., ge=1, le=1000000, description="Количество звёзд (1-1000000)")

    @field_validator('recipient_username')
    @classmethod
    def validate_username(cls, v):
        # Убираем @ если есть
        if v.startswith('@'):
            v = v[1:]
        
        # Проверяем формат
        if not re.match(r'^[a-zA-Z0-9_]{5,32}$', v):
            raise ValueError('Username должен содержать только буквы, цифры и подчёркивания (5-32 символа)')
        
        return v


class BuyStarsResponse(BaseModel):
    """Ответ на покупку звёзд"""
    success: bool
    purchase_id: int
    stars_amount: int
    recipient_username: str
    price_paid_ton: float
    fragment_tx_id: Optional[str] = None
    status: str


class StarsPurchaseResponse(BaseModel):
    """Информация о покупке звёзд"""
    id: int
    recipient_username: str
    stars_amount: int
    price_nanotons: int
    fragment_cost_ton: Optional[float]
    fragment_tx_id: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: datetime

    @property
    def price_ton(self) -> float:
        """Цена в TON"""
        return self.price_nanotons / 1e9

    class Config:
        from_attributes = True


class StarsPurchaseListResponse(BaseModel):
    """Список покупок звёзд"""
    purchases: list[StarsPurchaseResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class FragmentUserInfoResponse(BaseModel):
    """Ответ Fragment с информацией о пользователе"""
    model_config = ConfigDict(extra="allow")

    success: Optional[bool] = Field(None, description="Успешность запроса")
    username: Optional[str] = Field(None, description="Telegram username пользователя")


# Premium Purchase схемы
class PremiumPriceResponse(BaseModel):
    """Ответ с ценой Telegram Premium"""
    months: int = Field(..., description="Количество месяцев")
    fragment_price_ton: float = Field(..., description="Цена Fragment в TON")
    markup_percent: int = Field(..., description="Наценка маркета в %")
    final_price_ton: float = Field(..., description="Итоговая цена в TON")
    final_price_nanotons: int = Field(..., description="Итоговая цена в nanotons")
    price_per_month: float = Field(..., description="Цена за месяц в TON")


class BuyPremiumRequest(BaseModel):
    """Запрос на покупку Telegram Premium"""
    username: str = Field(
        ..., 
        description="Telegram username (без @)",
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]{2,31}$"
    )
    months: int = Field(
        ..., 
        description="Длительность подписки в месяцах (3, 6 или 12)"
    )
    show_sender: bool = Field(
        default=False, 
        description="Показывать отправителя"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "durov",
                "months": 3,
                "show_sender": False
            }
        }


class PremiumSenderInfo(BaseModel):
    """Информация об отправителе"""
    phone_number: Optional[str] = Field(None, description="Номер телефона")
    name: Optional[str] = Field(None, description="Имя отправителя")


class BuyPremiumResponse(BaseModel):
    """Ответ на покупку Telegram Premium"""
    success: bool = Field(..., description="Успешность операции")
    id: Optional[str] = Field(None, description="UUID транзакции")
    receiver: Optional[str] = Field(None, description="Username получателя")
    goods_quantity: Optional[int] = Field(None, description="Количество месяцев")
    sender: Optional[PremiumSenderInfo] = Field(None, description="Информация об отправителе")
    ton_price: Optional[str] = Field(None, description="Цена в TON")
    ref_id: Optional[str] = Field(None, description="Reference ID")
    status: Optional[str] = Field(None, description="Статус транзакции")
    type: Optional[str] = Field(None, description="Тип транзакции")
    error: Optional[str] = Field(None, description="Сообщение об ошибке")
    created_at: Optional[str] = Field(None, description="Дата создания")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
                "receiver": "durov",
                "goods_quantity": 3,
                "sender": {
                    "phone_number": "+1234567890",
                    "name": "John Doe"
                },
                "ton_price": "15.5",
                "ref_id": "ref123",
                "status": "completed",
                "type": "premium",
                "error": None,
                "created_at": "2025-12-26T14:15:22Z"
            }
        }
