"""Сервис для работы со звёздами"""

import re
from typing import Dict, Any

from app.configs import settings
from app.db.models import User
from app.integrations.fragment import FragmentIntegration
from app.utils.logger import get_logger

from .exceptions import *


logger = get_logger(__name__)


class StarsService:
    """Бизнес-логика покупки звёзд"""

    def __init__(self):
        self.fragment = FragmentIntegration()

    def validate_username(self, username: str) -> str:
        """
        Валидация и нормализация username.
        
        Args:
            username: Username с @ или без
            
        Returns:
            Нормализованный username без @
            
        Raises:
            InvalidUsernameError: Если username некорректный
        """
        if not username:
            raise InvalidUsernameError(username)
        
        # Убираем @ если есть
        if username.startswith("@"):
            username = username[1:]
        
        # Проверяем формат username (5-32 символа, только буквы, цифры, подчёркивания)
        if not re.match(r"^[a-zA-Z0-9_]{5,32}$", username):
            raise InvalidUsernameError(username)
        
        return username

    # Допустимые грейды звезд в Fragment
    ALLOWED_STAR_GRADES = [50, 100, 150, 250, 350, 500, 750, 1000, 1500, 2500, 5000, 10000, 25000, 50000, 100000, 150000, 500000, 1000000]

    def validate_stars_amount(self, amount: int) -> None:
        """
        Валидация количества звёзд.
        Fragment API поддерживает только конкретные грейды.
        
        Args:
            amount: Количество звёзд
            
        Raises:
            StarsAmountError: Если количество некорректное или не соответствует грейду
        """
        if not isinstance(amount, int):
            raise StarsAmountError(amount)
        
        if amount not in self.ALLOWED_STAR_GRADES:
            raise StarsAmountError(amount)

    def validate_user_balance(self, user: User, required_nanotons: int) -> None:
        """
        Проверка баланса пользователя.
        
        Args:
            user: Пользователь
            required_nanotons: Требуемая сумма в nanotons
            
        Raises:
            InsufficientBalanceError: Если недостаточно средств
        """
        if user.market_balance < required_nanotons:
            raise InsufficientBalanceError(required_nanotons, user.market_balance)

    async def get_stars_price_with_markup(self, stars_amount: int) -> Dict[str, Any]:
        """
        Получить цену звёзд с наценкой маркета.
        
        Args:
            stars_amount: Количество звёзд
            
        Returns:
            Dict с информацией о цене
        """
        try:
            # Получаем цену от Fragment
            fragment_price = await self.fragment.get_stars_price(stars_amount)
            
            # Добавляем наценку
            base_price_ton = fragment_price.get("cost_ton", 0)
            markup_multiplier = 1 + (settings.stars_markup_percent / 100)
            final_price_ton = base_price_ton * markup_multiplier
            final_price_nanotons = int(final_price_ton * 1e9)
            
            return {
                "stars_amount": stars_amount,
                "fragment_price_ton": base_price_ton,
                "markup_percent": settings.stars_markup_percent,
                "final_price_ton": final_price_ton,
                "final_price_nanotons": final_price_nanotons,
                "profit_ton": final_price_ton - base_price_ton
            }
            
        except Exception as e:
            logger.error(f"Error getting stars price: {e}")
            raise FragmentAPIError(f"Failed to get price: {str(e)}")

    async def buy_stars_via_fragment(
        self, 
        recipient_username: str, 
        stars_amount: int,
        bank_account = None  # Банк-аккаунт для покупки
    ) -> Dict[str, Any]:
        """
        Купить звёзды через Fragment API от имени банк-аккаунта.
        
        Args:
            recipient_username: Username получателя (без @)
            stars_amount: Количество звёзд
            bank_account: Банк-аккаунт маркета (опционально)
            
        Returns:
            Dict с результатом покупки
        """
        # Если передан банк-аккаунт, используем его для авторизации
        if bank_account:
            logger.info(f"Buying stars via bank account: {bank_account.telegram_id}")
        
        # Вызываем Fragment API - исключения пробрасываются напрямую
        result = await self.fragment.buy_stars(recipient_username, stars_amount)
        
        # Fragment API возвращает success=true при успехе
        if not result.get("success", False):
            error_msg = result.get("error") or "Unknown error"
            raise FragmentAPIError(f"Purchase failed: {error_msg}")
        
        return result

    def calculate_profit(self, user_paid_nanotons: int, fragment_cost_ton: float) -> int:
        """
        Рассчитать прибыль маркета.
        
        Args:
            user_paid_nanotons: Сколько заплатил пользователь в nanotons
            fragment_cost_ton: Реальная стоимость Fragment в TON
            
        Returns:
            Прибыль в nanotons
        """
        fragment_cost_nanotons = int(fragment_cost_ton * 1e9)
        return user_paid_nanotons - fragment_cost_nanotons

    async def get_premium_price_with_markup(self, months: int) -> Dict[str, Any]:
        """
        Получить цену Telegram Premium с наценкой маркета.
        
        Args:
            months: Количество месяцев (3, 6 или 12)
            
        Returns:
            Dict с информацией о цене
        """
        # Валидация
        if months not in (3, 6, 12):
            from .exceptions import PremiumMonthsError
            raise PremiumMonthsError(months)
        
        # Получаем цену от Fragment
        fragment_price = await self.fragment.get_premium_price(months)
        
        # Добавляем наценку
        base_price_ton = fragment_price.get("cost_ton", 0)
        markup_multiplier = 1 + (settings.stars_markup_percent / 100)
        final_price_ton = base_price_ton * markup_multiplier
        final_price_nanotons = int(final_price_ton * 1e9)
        
        return {
            "months": months,
            "fragment_price_ton": base_price_ton,
            "markup_percent": settings.stars_markup_percent,
            "final_price_ton": final_price_ton,
            "final_price_nanotons": final_price_nanotons,
            "price_per_month": final_price_ton / months
        }

    async def get_fragment_user_info(self, username: str) -> Dict[str, Any]:
        """
        Получить информацию о пользователе через Fragment API.
        
        Args:
            username: Telegram username (без @)
            
        Returns:
            Dict с информацией о пользователе
        """
        try:
            response = await self.fragment.get_user_info(username)
            return response
        except Exception as e:
            logger.error(f"Error getting Fragment user info: {e}")
            raise FragmentAPIError(f"Failed to get user info: {str(e)}")
