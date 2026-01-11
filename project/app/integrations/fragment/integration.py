"""Fragment API интеграция"""

import re
from typing import Any, Dict
import aiohttp

from app.configs import settings
from app.utils.logger import get_logger
from app.modules.stars.exceptions import (
    FragmentAPIError,
    FragmentUserNotFoundError,
    FragmentKYCRequiredError,
    FragmentTONNetworkError,
    FragmentInsufficientFundsError
)


logger = get_logger(__name__)


class FragmentIntegration:
    """
    Интеграция с Fragment API для покупки звёзд.
    
    Документация: https://api.fragment-api.com/docs
    Минимум: 100 звезд
    Максимум: 150 000 звезд
    """

    market_name = "fragment"
    base_url = "https://api.fragment-api.com/v1"

    def __init__(self):
        self.logger = get_logger("FragmentAPI")
        # Используем JWT токен напрямую из настроек
        self.auth_token = settings.fragment_api_key
        
        if not self.auth_token:
            self.logger.warning("Fragment API key not found - Fragment integration will be disabled")
            self.auth_token = None
        else:
            self.logger.info("Fragment API initialized with JWT token")

    async def authenticate(self) -> str:
        """
        Возвращает JWT токен для аутентификации.
        JWT токен уже готов к использованию.
        """
        return self.auth_token

    async def _make_request(
        self, 
        method: str, 
        url: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Выполнить HTTP запрос к Fragment API"""
        if not self.auth_token:
            raise FragmentAPIError("Fragment API is disabled - no auth token")
            
        # Добавляем JWT токен в заголовки
        headers = kwargs.pop("headers", {})
        headers.update({
            "Authorization": self.auth_token,
            "Accept": "application/json"
        })
        
        self.logger.debug(f"Making {method} request to {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, **kwargs) as response:
                self.logger.debug(f"Response status: {response.status}")
                
                if response.status < 200 or response.status >= 300:
                    error_text = await response.text()
                    self.logger.error(f"Fragment API error: {response.status} - {error_text}")
                    
                    # Парсим error code из JSON ответа
                    # Формат: {"errors":[{"code":"20","error":"..."}]}
                    error_code = None
                    error_message = error_text
                    try:
                        code_match = re.search(r'"code"\s*:\s*"(\d+)"', error_text)
                        if code_match:
                            error_code = int(code_match.group(1))
                        
                        msg_match = re.search(r'"error"\s*:\s*"([^"]+)"', error_text)
                        if msg_match:
                            error_message = msg_match.group(1)
                    except:
                        pass
                    
                    # Выбрасываем типизированное исключение
                    if error_code == 20:
                        username = kwargs.get("json", {}).get("username", "unknown")
                        raise FragmentUserNotFoundError(username)
                    elif error_code == 11:
                        raise FragmentKYCRequiredError()
                    elif error_code in (10, 12, 13):
                        raise FragmentTONNetworkError(error_message, error_code)
                    elif error_code == 0 and "not enough funds" in error_text.lower():
                        raise FragmentInsufficientFundsError(error_message)
                    else:
                        raise FragmentAPIError(f"Fragment API error: {response.status} - {error_text}")
                
                return await response.json()

    async def get_stars_price(self, stars_amount: int) -> Dict[str, Any]:
        """
        Получить цену звёзд в TON.
        
        Args:
            stars_amount: Количество звёзд (100-150000)
            
        Returns:
            Dict с информацией о цене
        """
        try:
            # Fragment API использует фиксированную цену: 1 звезда = 0.013 TON
            price_per_star = 0.013
            total_price = stars_amount * price_per_star
            
            response = {
                "stars_amount": stars_amount,
                "cost_ton": total_price,
                "price_per_star": price_per_star,
                "currency": "TON"
            }
            
            self.logger.info(f"Fragment price for {stars_amount} stars: {total_price:.4f} TON")
            return response
            
        except Exception as e:
            self.logger.error(f"Error calculating stars price: {e}")
            raise

    async def get_premium_price(self, months: int) -> Dict[str, Any]:
        """
        Получить цену Telegram Premium в TON.
        
        Args:
            months: Количество месяцев (3, 6 или 12)
            
        Returns:
            Dict с информацией о цене
        """
        # Примерные цены Premium на Fragment (могут меняться)
        # Актуальные цены: https://fragment.com/premium
        PREMIUM_PRICES_TON = {
            3: 7.5,    # ~2.5 TON/месяц
            6: 13.0,   # ~2.17 TON/месяц
            12: 23.0,  # ~1.92 TON/месяц
        }
        
        if months not in PREMIUM_PRICES_TON:
            raise ValueError(f"Invalid months value: {months}. Must be 3, 6 or 12")
        
        price_ton = PREMIUM_PRICES_TON[months]
        
        response = {
            "months": months,
            "cost_ton": price_ton,
            "price_per_month": price_ton / months,
            "currency": "TON"
        }
        
        self.logger.info(f"Fragment price for {months} months premium: {price_ton:.2f} TON")
        return response

    async def buy_stars(
        self, 
        recipient_username: str, 
        stars_amount: int
    ) -> Dict[str, Any]:
        """
        Купить звёзды через Fragment API.
        
        Args:
            recipient_username: Username получателя (без @)
            stars_amount: Количество звёзд (100-150000)
            
        Returns:
            Dict с результатом покупки
        """
        # Убираем @ если есть
        if recipient_username.startswith("@"):
            recipient_username = recipient_username[1:]
        
        try:
            order_data = {
                "username": recipient_username,
                "quantity": stars_amount,
                "show_sender": False
            }
            
            response = await self._make_request(
                method="POST",
                url=f"{self.base_url}/order/stars/",
                json=order_data
            )
            
            self.logger.info(
                f"Fragment stars purchase completed",
                extra={
                    "recipient": recipient_username,
                    "stars": stars_amount,
                    "response": response
                }
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                f"Error buying stars",
                extra={
                    "recipient": recipient_username,
                    "stars": stars_amount,
                    "error": str(e)
                }
            )
            raise

    async def check_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Проверить статус транзакции.
        
        Args:
            transaction_id: ID транзакции Fragment
            
        Returns:
            Dict со статусом транзакции
        """
        try:
            response = await self._make_request(
                method="GET",
                url=f"{self.base_url}/transaction/{transaction_id}"
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error checking transaction status: {e}")
            raise

    async def buy_premium(
        self,
        username: str,
        months: int,
        show_sender: bool = False
    ) -> Dict[str, Any]:
        """
        Купить Telegram Premium подписку через Fragment API.
        
        POST https://api.fragment-api.com/v1/order/premium/
        
        Args:
            username: Telegram username получателя (без @), паттерн: [a-zA-Z][a-zA-Z0-9_]{2,31}$
            months: Длительность подписки (3, 6 или 12 месяцев)
            show_sender: Показывать отправителя (default: False)
            
        Returns:
            Dict с результатом покупки:
            - success: bool
            - id: str (UUID транзакции)
            - receiver: str
            - goods_quantity: int
            - sender: {phone_number, name}
            - ton_price: str
            - ref_id: str
            - status: str
            - type: str
            - error: str | null
            - created_at: str
            
        Error codes:
            0 - General error code
            10 - TON Network error code
            11 - KYC is needed for specified account
            12 - TON Network connection error
            13 - General TON / Telegram error
            20 - Recipient username was not found on Fragment
        """
        # Убираем @ если есть
        if username.startswith("@"):
            username = username[1:]
        
        # Валидация months
        if months not in (3, 6, 12):
            raise ValueError(f"Invalid months value: {months}. Must be 3, 6 or 12")
        
        try:
            order_data = {
                "username": username,
                "months": months,
                "show_sender": show_sender
            }
            
            response = await self._make_request(
                method="POST",
                url=f"{self.base_url}/order/premium/",
                json=order_data
            )
            
            self.logger.info(
                f"Fragment premium purchase completed",
                extra={
                    "recipient": username,
                    "months": months,
                    "response": response
                }
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                f"Error buying premium",
                extra={
                    "recipient": username,
                    "months": months,
                    "error": str(e)
                }
            )
            raise

    async def get_user_info(self, username: str) -> Dict[str, Any]:
        """
        Получить информацию о пользователе через Fragment API.
        
        GET https://api.fragment-api.com/v1/user/{username}/
        
        Args:
            username: Telegram username (без @)
            
        Returns:
            Dict с информацией о пользователе
        """
        if username.startswith("@"):
            username = username[1:]
        
        try:
            response = await self._make_request(
                method="GET",
                url=f"{self.base_url}/user/{username}/"
            )
            
            self.logger.info(
                "Fragment user info received",
                extra={
                    "username": username,
                    "response": response
                }
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                "Error getting Fragment user info",
                extra={
                    "username": username,
                    "error": str(e)
                }
            )
            raise
