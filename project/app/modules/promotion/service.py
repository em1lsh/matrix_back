"""Сервис продвижения NFT"""

import os
from datetime import datetime, timedelta
from typing import Tuple

from app.db.models import User, NFT
from .exceptions import (
    InsufficientBalanceError,
    InvalidPromotionPeriodError,
    NFTNotFoundError,
    NFTNotOwnedError,
    PromotionAlreadyActiveError,
)


class PromotionService:
    """Сервис для работы с продвижением NFT"""

    def __init__(self):
        # Получаем стоимость из переменных окружения (по умолчанию 0.1 TON)
        self.daily_cost_nanotons = int(
            os.getenv("NFT_PROMOTION_DAILY_COST", "100000000")  # 0.1 TON в nanotons
        )

    def calculate_promotion_cost(self, days: int) -> Tuple[int, float]:
        """
        Рассчитать стоимость продвижения с учетом скидки.
        
        Args:
            days: Количество дней продвижения
            
        Returns:
            Tuple[int, float]: (стоимость в nanotons, процент скидки)
            
        Raises:
            InvalidPromotionPeriodError: Если неверный период
        """
        if days < 1 or days > 30:
            raise InvalidPromotionPeriodError(days)
        
        # Базовая стоимость
        base_cost = self.daily_cost_nanotons * days
        
        # Расчет скидки: 0.05 * (n-1), но не более 20%
        discount_percent = min(0.05 * (days - 1), 0.20)
        
        # Итоговая стоимость
        final_cost = int(base_cost * (1 - discount_percent))
        
        return final_cost, discount_percent

    def validate_nft_ownership(self, nft: NFT, user_id: int) -> None:
        """
        Проверить, что NFT принадлежит пользователю.
        
        Args:
            nft: NFT объект
            user_id: ID пользователя
            
        Raises:
            NFTNotOwnedError: Если NFT не принадлежит пользователю
        """
        if nft.user_id != user_id:
            raise NFTNotOwnedError(nft.id)

    def validate_user_balance(self, user: User, required_amount: int) -> None:
        """
        Проверить баланс пользователя.
        
        Args:
            user: Пользователь
            required_amount: Требуемая сумма в nanotons
            
        Raises:
            InsufficientBalanceError: Если недостаточно средств
        """
        if user.market_balance < required_amount:
            raise InsufficientBalanceError(required_amount, user.market_balance)

    def calculate_promotion_end_time(self, days: int, current_end_time: datetime = None) -> datetime:
        """
        Рассчитать время окончания продвижения.
        
        Args:
            days: Количество дней
            current_end_time: Текущее время окончания (для продления)
            
        Returns:
            datetime: Новое время окончания
        """
        if current_end_time and current_end_time > datetime.utcnow():
            # Продление активного продвижения
            return current_end_time + timedelta(days=days)
        else:
            # Новое продвижение
            return datetime.utcnow() + timedelta(days=days)