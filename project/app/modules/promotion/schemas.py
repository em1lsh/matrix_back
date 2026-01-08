"""Схемы модуля продвижения NFT"""

from datetime import datetime
from pydantic import BaseModel, Field, validator


class PromotionCalculationRequest(BaseModel):
    """Запрос расчета стоимости продвижения"""
    
    days: int = Field(..., ge=1, le=30, description="Количество дней продвижения (1-30)")


class PromotionCalculationResponse(BaseModel):
    """Ответ с расчетом стоимости продвижения"""
    
    days: int = Field(..., description="Количество дней")
    base_cost_ton: float = Field(..., description="Базовая стоимость в TON")
    discount_percent: float = Field(..., description="Процент скидки")
    final_cost_ton: float = Field(..., description="Итоговая стоимость в TON")
    savings_ton: float = Field(..., description="Экономия в TON")


class PromoteNFTRequest(BaseModel):
    """Запрос на продвижение NFT"""
    
    nft_id: int = Field(..., description="ID NFT для продвижения")
    days: int = Field(..., ge=1, le=30, description="Количество дней продвижения (1-30)")


class ExtendPromotionRequest(BaseModel):
    """Запрос на продление продвижения NFT"""
    
    nft_id: int = Field(..., description="ID NFT для продления продвижения")
    days: int = Field(..., ge=1, le=30, description="Количество дней для продления (1-30)")


class PromotionResponse(BaseModel):
    """Ответ о продвижении NFT"""
    
    id: int = Field(..., description="ID продвижения")
    nft_id: int = Field(..., description="ID NFT")
    user_id: int = Field(..., description="ID пользователя")
    created_at: datetime = Field(..., description="Время создания")
    ends_at: datetime = Field(..., description="Время окончания")
    total_costs_ton: float = Field(..., description="Общая стоимость в TON")
    is_active: bool = Field(..., description="Активно ли продвижение")
    
    class Config:
        from_attributes = True


class PromotionOperationResponse(BaseModel):
    """Ответ об операции с продвижением"""
    
    success: bool = Field(..., description="Успешность операции")
    promotion: PromotionResponse = Field(..., description="Данные продвижения")
    cost_ton: float = Field(..., description="Стоимость операции в TON")
    new_balance_ton: float = Field(..., description="Новый баланс пользователя в TON")