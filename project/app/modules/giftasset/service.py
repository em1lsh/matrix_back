"""
Gift Asset API сервис для работы с внешним API giftasset.pro
"""
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

from app.utils.logger import logger
from app.modules.giftasset.exceptions import (
    GiftAssetAPIException,
    GiftAssetUnauthorizedException,
    GiftAssetRateLimitException
)


class GiftAssetAPIService:
    """Сервис для работы с Gift Asset API"""
    
    def __init__(self, base_url: str = "https://giftasset.pro", api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_delay = 0.2  # 5 RPS = 0.2 seconds between requests
        self._last_request_time = 0.0
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить HTTP сессию"""
        if self.session is None or self.session.closed:
            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
                
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout
            )
        return self.session
    
    async def close(self):
        """Закрыть HTTP сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Выполнить HTTP запрос к Gift Asset API"""
        # Rate limiting: 5 RPS
        import time
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        if time_since_last_request < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay - time_since_last_request)
        self._last_request_time = time.time()
        
        url = urljoin(self.base_url, endpoint)
        session = await self._get_session()
        
        try:
            async with session.request(method, url, **kwargs) as response:
                if response.status == 401:
                    raise GiftAssetUnauthorizedException("Invalid API key")
                elif response.status == 429:
                    raise GiftAssetRateLimitException("Rate limit exceeded")
                elif response.status >= 400:
                    error_text = await response.text()
                    raise GiftAssetAPIException(f"API error {response.status}: {error_text}")
                
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"Gift Asset API request failed: {e}")
            raise GiftAssetAPIException(f"Request failed: {str(e)}")
    
    async def get_gifts_price_list(self, models: bool = False, premarket: bool = False) -> Dict[str, Any]:
        """Получить список цен подарков
        
        По умолчанию models=False, чтобы избежать ошибки 400
        """
        params = {"models": "false"}  # Явно указываем models=false по умолчанию
        if models:
            params["models"] = "true"
        if premarket:
            params["premarket"] = "true"
            
        return await self._make_request("GET", "/api/v1/gifts/get_gifts_price_list", params=params)
    
    async def get_collections_volumes(self) -> Dict[str, Any]:
        """Получить объемы продаж коллекций"""
        return await self._make_request("GET", "/api/v1/gifts/get_collections_volumes")
    
    async def get_collections_week_volumes(self) -> Dict[str, Any]:
        """Получить недельные объемы продаж коллекций"""
        return await self._make_request("GET", "/api/v1/gifts/get_collections_week_volumes")
    
    async def get_collections_month_volumes(self) -> Dict[str, Any]:
        """Получить месячные объемы продаж коллекций"""
        return await self._make_request("GET", "/api/v1/gifts/get_collections_month_volumes")
    
    async def get_gifts_collections_emission(self) -> Dict[str, Any]:
        """Получить данные об эмиссии коллекций"""
        return await self._make_request("GET", "/api/v1/gifts/get_gifts_collections_emission")
    
    async def get_gifts_collections_health_index(self) -> Dict[str, Any]:
        """Получить индекс здоровья коллекций"""
        return await self._make_request("GET", "/api/v1/gifts/get_gifts_collections_health_index")
    
    async def get_gifts_collections_marketcap(self) -> Dict[str, Any]:
        """Получить рыночную капитализацию коллекций"""
        return await self._make_request("GET", "/api/v1/gifts/get_gifts_collections_marketcap")
    
    async def get_gifts_price_list_history(self) -> Dict[str, Any]:
        """Получить историю цен"""
        return await self._make_request("GET", "/api/v1/gifts/get_gifts_price_list_history")
    
    async def get_providers_volumes(self) -> Dict[str, Any]:
        """Получить объемы продаж провайдеров
        
        API возвращает список, преобразуем в словарь {provider: stats}
        """
        data = await self._make_request("GET", "/api/v1/gifts/get_providers_volumes")
        
        # Если данные уже в формате dict, возвращаем как есть
        if isinstance(data, dict):
            return data
        
        # Если данные в формате list, преобразуем в dict
        if isinstance(data, list):
            result = {}
            for item in data:
                if isinstance(item, dict) and "provider" in item:
                    provider = item.pop("provider")
                    result[provider] = item
            return result
        
        return data
    
    async def get_providers_fee(self) -> Dict[str, Any]:
        """Получить комиссии провайдеров
        
        API возвращает список, преобразуем в словарь {provider: fee}
        """
        data = await self._make_request("GET", "/api/v1/gifts/get_providers_fee")
        
        # Если данные уже в формате dict, возвращаем как есть
        if isinstance(data, dict):
            return data
        
        # Если данные в формате list, преобразуем в dict
        if isinstance(data, list):
            result = {}
            for item in data:
                if isinstance(item, dict):
                    # Ищем ключи provider и fee
                    provider = item.get("provider") or item.get("name")
                    fee = item.get("fee") or item.get("commission")
                    if provider is not None and fee is not None:
                        result[provider] = fee
            return result
        
        return data
    
    async def get_all_providers_sales_history(self) -> List[Dict[str, Any]]:
        """Получить историю продаж всех провайдеров"""
        return await self._make_request("GET", "/api/v1/gifts/get_all_providers_sales_history")
    
    async def get_providers_sales_history(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Получить историю продаж провайдеров"""
        params = {}
        if provider:
            params["provider"] = provider
        return await self._make_request("GET", "/api/v1/gifts/get_providers_sales_history", params=params)
    
    async def get_all_collections_by_user(self, username: str, include: Optional[List[str]] = None, 
                                        exclude: Optional[List[str]] = None, limit: Optional[int] = None,
                                        offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получить коллекции пользователя"""
        params = {"username": username}
        
        json_data = {}
        if include:
            json_data["include"] = include
        if exclude:
            json_data["exclude"] = exclude
        if limit:
            json_data["limit"] = limit
        if offset:
            json_data["offset"] = offset
            
        kwargs = {"params": params}
        if json_data:
            kwargs["json"] = json_data
            
        return await self._make_request("POST", "/api/v1/gifts/get_all_collections_by_user", **kwargs)
    
    async def get_attribute_volumes(self) -> Dict[str, Any]:
        """Получить объемы продаж атрибутов"""
        return await self._make_request("GET", "/api/v1/gifts/get_attribute_volumes")
    
    async def get_attributes_metadata(self) -> List[Dict[str, Any]]:
        """Получить метаданные атрибутов"""
        return await self._make_request("GET", "/api/v1/gifts/get_attributes_metadata")
    
    async def get_collections_metadata(self) -> List[Dict[str, Any]]:
        """Получить метаданные коллекций
        
        API возвращает List[Dict[collection_name, metadata]]
        Преобразуем в плоский список [{name, metadata}]
        """
        data = await self._make_request("GET", "/api/v1/gifts/get_collections_metadata")
        
        # Если данные уже в правильном формате (список словарей с полями name/metadata)
        if isinstance(data, list) and len(data) > 0:
            first_item = data[0]
            if isinstance(first_item, dict):
                # Проверяем, есть ли уже поля name и metadata
                if "name" in first_item or "collection_name" in first_item:
                    return data
                
                # Преобразуем формат {collection_name: metadata} в [{name, ...metadata}]
                result = []
                for item in data:
                    for collection_name, metadata in item.items():
                        if isinstance(metadata, dict):
                            result.append({
                                "name": collection_name,
                                **metadata
                            })
                        else:
                            result.append({
                                "name": collection_name,
                                "metadata": metadata
                            })
                return result
        
        return data
    
    async def get_collection_offers(self, collection_name: str) -> Dict[str, Any]:
        """Получить офферы на коллекцию"""
        json_data = {"collection_name": collection_name}
        return await self._make_request("POST", "/api/v1/gifts/get_collection_offers", json=json_data)
    
    async def get_gifts_update_stat(self) -> Dict[str, Any]:
        """Получить статистику обновлений"""
        return await self._make_request("GET", "/api/v1/gifts/get_gifts_update_stat")
    
    async def get_top_best_deals(self) -> List[Dict[str, Any]]:
        """Получить топ лучших сделок"""
        return await self._make_request("GET", "/api/v1/gifts/get_top_best_deals")
    
    async def get_unique_deals(self) -> List[Dict[str, Any]]:
        """Получить уникальные сделки"""
        return await self._make_request("GET", "/api/v1/gifts/get_unique_deals")
    
    async def get_unique_gifts_price_list(self) -> Dict[str, Any]:
        """Получить цены уникальных подарков"""
        return await self._make_request("GET", "/api/v1/gifts/get_unique_gifts_price_list")
    
    async def get_unique_last_sales(self) -> List[Dict[str, Any]]:
        """Получить последние продажи уникальных подарков"""
        return await self._make_request("GET", "/api/v1/gifts/get_unique_last_sales")


# Глобальный экземпляр сервиса
# API ключ будет загружен из переменных окружения
import os
GIFTASSET_API_KEY = os.getenv("GIFTASSET_API_KEY")
gift_asset_service = GiftAssetAPIService(api_key=GIFTASSET_API_KEY)