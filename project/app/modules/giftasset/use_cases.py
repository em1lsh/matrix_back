"""
Gift Asset use cases
"""
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.giftasset.repository import GiftAssetRepository
from app.modules.giftasset.service import gift_asset_service
from app.modules.giftasset.exceptions import (
    GiftAssetDataNotFoundException,
    GiftAssetAPIException,
    GiftAssetCacheException
)
from app.utils.cache import build_cache_key, get_cached, set_cached
from app.utils.logger import logger


class GiftAssetUseCases:
    """Use cases для Gift Asset API"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = GiftAssetRepository(session)
    
    async def get_gifts_price_list(self, models: bool = False, premarket: bool = False, 
                                 force_refresh: bool = False) -> Dict[str, Any]:
        """Получить список цен подарков"""
        try:
            # Проверяем кеш, если не требуется принудительное обновление
            if not force_refresh:
                cached_data = await self.repository.get_price_list(include_models=models)
                if cached_data["collection_floors"]:
                    return cached_data
            
            # Получаем свежие данные из API
            api_data = await gift_asset_service.get_gifts_price_list(models=models, premarket=premarket)
            
            # Сохраняем в кеш
            await self.repository.update_price_list(api_data)
            
            # Обновляем статистику
            await self.repository.update_endpoint_stat("get_gifts_price_list", "success")
            
            return api_data
            
        except GiftAssetAPIException as e:
            # При ошибке API пытаемся вернуть кешированные данные
            logger.warning(f"Gift Asset API error, trying cache: {e}")
            cached_data = await self.repository.get_price_list(include_models=models)
            if cached_data["collection_floors"]:
                await self.repository.update_endpoint_stat("get_gifts_price_list", "error", str(e))
                return cached_data
            raise GiftAssetDataNotFoundException("No cached price data available")
        
        except Exception as e:
            await self.repository.update_endpoint_stat("get_gifts_price_list", "error", str(e))
            logger.error(f"Failed to get gifts price list: {e}")
            raise GiftAssetCacheException(f"Failed to get price list: {str(e)}")

    async def get_gifts_price_list_history(self) -> Dict[str, Any]:
        """Получить историю цен подарков"""
        cache_key = build_cache_key("giftasset:price_list_history")
        cached = await get_cached(cache_key)
        if cached:
            try:
                cached_value = cached.decode() if isinstance(cached, (bytes, bytearray)) else cached
                return json.loads(cached_value)
            except Exception as e:
                logger.warning(f"Failed to decode cached price list history: {e}")

        try:
            data = await self.repository.get_gifts_price_list_history()
            await set_cached(cache_key, json.dumps(data), expire=300)
            return data
        except GiftAssetAPIException as e:
            logger.warning(f"Gift Asset API error while fetching price list history: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get gifts price list history: {e}")
            raise GiftAssetCacheException(f"Failed to get price list history: {str(e)}")
    
    async def get_collections_volumes(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Получить объемы продаж коллекций"""
        try:
            # Проверяем кеш
            if not force_refresh:
                cached_data = await self.repository.get_collections_volumes()
                if cached_data["collections"]:
                    return cached_data
            
            # Получаем свежие данные из API
            api_data = await gift_asset_service.get_collections_volumes()
            
            # Сохраняем в кеш
            await self.repository.update_collections_volumes(api_data)
            
            # Обновляем статистику
            await self.repository.update_endpoint_stat("get_collections_volumes", "success", frequency_minutes=60)
            
            return {"collections": api_data}
            
        except GiftAssetAPIException as e:
            logger.warning(f"Gift Asset API error, trying cache: {e}")
            cached_data = await self.repository.get_collections_volumes()
            if cached_data["collections"]:
                await self.repository.update_endpoint_stat("get_collections_volumes", "error", str(e))
                return cached_data
            raise GiftAssetDataNotFoundException("No cached volumes data available")
        
        except Exception as e:
            await self.repository.update_endpoint_stat("get_collections_volumes", "error", str(e))
            logger.error(f"Failed to get collections volumes: {e}")
            raise GiftAssetCacheException(f"Failed to get volumes: {str(e)}")
    
    async def get_collections_emission(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Получить данные об эмиссии коллекций"""
        try:
            # Проверяем кеш
            if not force_refresh:
                cached_data = await self.repository.get_collections_emission()
                if cached_data["collections"]:
                    return cached_data
            
            # Получаем свежие данные из API
            api_data = await gift_asset_service.get_gifts_collections_emission()
            
            # Сохраняем в кеш
            await self.repository.update_collections_emission(api_data)
            
            # Обновляем статистику
            await self.repository.update_endpoint_stat("get_gifts_collections_emission", "success", frequency_minutes=1440)  # раз в сутки
            
            return {"collections": api_data}
            
        except GiftAssetAPIException as e:
            logger.warning(f"Gift Asset API error, trying cache: {e}")
            cached_data = await self.repository.get_collections_emission()
            if cached_data["collections"]:
                await self.repository.update_endpoint_stat("get_gifts_collections_emission", "error", str(e))
                return cached_data
            raise GiftAssetDataNotFoundException("No cached emission data available")
        
        except Exception as e:
            await self.repository.update_endpoint_stat("get_gifts_collections_emission", "error", str(e))
            logger.error(f"Failed to get collections emission: {e}")
            raise GiftAssetCacheException(f"Failed to get emission: {str(e)}")
    
    async def get_collections_health_index(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Получить индекс здоровья коллекций"""
        try:
            # Проверяем кеш
            if not force_refresh:
                cached_data = await self.repository.get_collections_health_index()
                if cached_data["collections"]:
                    return cached_data
            
            # Получаем свежие данные из API
            api_data = await gift_asset_service.get_gifts_collections_health_index()
            
            # Сохраняем в кеш
            await self.repository.update_collections_health_index(api_data)
            
            # Обновляем статистику
            await self.repository.update_endpoint_stat("get_gifts_collections_health_index", "success", frequency_minutes=1440)
            
            return {"collections": api_data}
            
        except GiftAssetAPIException as e:
            logger.warning(f"Gift Asset API error, trying cache: {e}")
            cached_data = await self.repository.get_collections_health_index()
            if cached_data["collections"]:
                await self.repository.update_endpoint_stat("get_gifts_collections_health_index", "error", str(e))
                return cached_data
            raise GiftAssetDataNotFoundException("No cached health index data available")
        
        except Exception as e:
            await self.repository.update_endpoint_stat("get_gifts_collections_health_index", "error", str(e))
            logger.error(f"Failed to get collections health index: {e}")
            raise GiftAssetCacheException(f"Failed to get health index: {str(e)}")
    
    async def get_total_market_cap(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Получить общую рыночную капитализацию"""
        try:
            # Проверяем кеш
            if not force_refresh:
                cached_data = await self.repository.get_total_market_cap()
                if cached_data["total_market_cap"] > 0:
                    return cached_data
            
            # Получаем свежие данные из API
            api_data = await gift_asset_service.get_gifts_collections_marketcap()
            
            # Вычисляем общую капитализацию
            total_market_cap = 0.0
            collections_count = len(api_data)
            
            for collection_data in api_data.values():
                if isinstance(collection_data, dict) and "market_cap" in collection_data:
                    total_market_cap += collection_data["market_cap"]
            
            result = {
                "total_market_cap": total_market_cap,
                "collections_count": collections_count
            }
            
            # Сохраняем в кеш
            await self.repository.save_market_cap(total_market_cap, collections_count)
            
            # Обновляем статистику
            await self.repository.update_endpoint_stat("get_total_market_cap", "success", frequency_minutes=1440)
            
            return result
            
        except GiftAssetAPIException as e:
            logger.warning(f"Gift Asset API error, trying cache: {e}")
            cached_data = await self.repository.get_total_market_cap()
            if cached_data["total_market_cap"] > 0:
                await self.repository.update_endpoint_stat("get_total_market_cap", "error", str(e))
                return cached_data
            raise GiftAssetDataNotFoundException("No cached market cap data available")
        
        except Exception as e:
            await self.repository.update_endpoint_stat("get_total_market_cap", "error", str(e))
            logger.error(f"Failed to get total market cap: {e}")
            raise GiftAssetCacheException(f"Failed to get market cap: {str(e)}")
    
    async def get_total_market_cap_history(self, period: str = "7d", 
                                         include_previous: bool = False) -> Dict[str, Any]:
        """Получить историю общей рыночной капитализации"""
        try:
            return await self.repository.get_market_cap_history(period, include_previous)
        except Exception as e:
            logger.error(f"Failed to get market cap history: {e}")
            raise GiftAssetCacheException(f"Failed to get market cap history: {str(e)}")
    
    async def get_providers_stats(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Получить статистику провайдеров"""
        try:
            # Проверяем кеш
            if not force_refresh:
                cached_data = await self.repository.get_providers_stats()
                if cached_data["providers"]:
                    return cached_data
            
            # Получаем данные объемов и комиссий
            volumes_data = await gift_asset_service.get_providers_volumes()
            fee_data = await gift_asset_service.get_providers_fee()
            
            # Объединяем данные
            providers_stats = []
            for provider, volumes in volumes_data.items():
                provider_stat = {
                    "provider": provider,
                    "hour_revenue": volumes.get("hour_revenue", 0.0),
                    "hour_sales": volumes.get("hour_sales", 0),
                    "total_revenue": volumes.get("total_revenue", 0.0),
                    "total_sales": volumes.get("total_sales", 0),
                    "peak_hour": volumes.get("peak_hour"),
                    "peak_hour_revenue_percent": volumes.get("peak_hour_revenue_percent", 0.0),
                    "peak_hour_sales_percent": volumes.get("peak_hour_sales_percent", 0.0),
                    "fee": fee_data.get(provider, 0.0)
                }
                providers_stats.append(provider_stat)
            
            # Сохраняем в кеш
            await self.repository.update_providers_stats(providers_stats)
            
            # Обновляем статистику
            await self.repository.update_endpoint_stat("get_providers_stats", "success", frequency_minutes=60)
            
            return {"providers": providers_stats}
            
        except GiftAssetAPIException as e:
            logger.warning(f"Gift Asset API error, trying cache: {e}")
            cached_data = await self.repository.get_providers_stats()
            if cached_data["providers"]:
                await self.repository.update_endpoint_stat("get_providers_stats", "error", str(e))
                return cached_data
            raise GiftAssetDataNotFoundException("No cached providers stats available")
        
        except Exception as e:
            await self.repository.update_endpoint_stat("get_providers_stats", "error", str(e))
            logger.error(f"Failed to get providers stats: {e}")
            raise GiftAssetCacheException(f"Failed to get providers stats: {str(e)}")
    
    async def get_sales_history(self, force_refresh: bool = False, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить историю продаж"""
        try:
            # Проверяем кеш
            if not force_refresh:
                cached_data = await self.repository.get_sales_history(limit=limit)
                if cached_data:
                    return cached_data
            
            # Получаем свежие данные из API
            api_data = await gift_asset_service.get_all_providers_sales_history()
            
            # Сохраняем в кеш
            await self.repository.save_sales_history(api_data)
            
            # Обновляем статистику
            await self.repository.update_endpoint_stat("get_all_providers_sales_history", "success", frequency_minutes=5)
            
            return api_data[:limit] if len(api_data) > limit else api_data
            
        except GiftAssetAPIException as e:
            logger.warning(f"Gift Asset API error, trying cache: {e}")
            cached_data = await self.repository.get_sales_history(limit=limit)
            if cached_data:
                await self.repository.update_endpoint_stat("get_all_providers_sales_history", "error", str(e))
                return cached_data
            raise GiftAssetDataNotFoundException("No cached sales history available")
        
        except Exception as e:
            await self.repository.update_endpoint_stat("get_all_providers_sales_history", "error", str(e))
            logger.error(f"Failed to get sales history: {e}")
            raise GiftAssetCacheException(f"Failed to get sales history: {str(e)}")
    
    async def get_user_collections(self, username: str, include: Optional[List[str]] = None,
                                 exclude: Optional[List[str]] = None, limit: Optional[int] = None,
                                 offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получить коллекции пользователя"""
        try:
            api_data = await gift_asset_service.get_all_collections_by_user(
                username=username,
                include=include,
                exclude=exclude,
                limit=limit,
                offset=offset
            )
            
            # Обновляем статистику
            await self.repository.update_endpoint_stat("get_all_collections_by_user", "success", frequency_minutes=0)  # по требованию
            
            return api_data
            
        except Exception as e:
            await self.repository.update_endpoint_stat("get_all_collections_by_user", "error", str(e))
            logger.error(f"Failed to get user collections: {e}")
            raise GiftAssetAPIException(f"Failed to get user collections: {str(e)}")
    
    async def get_attribute_volumes(self) -> Dict[str, Any]:
        """Получить объемы продаж атрибутов
        
        API возвращает: {provider: {backdrops: [...], collections: [...]}}
        Нужно преобразовать в: {backdrops: [...], patterns: [...], models: [...]}
        """
        try:
            api_data = await gift_asset_service.get_attribute_volumes()
            
            # Объединяем данные от всех провайдеров
            all_backdrops = []
            all_patterns = []
            all_models = []
            
            for provider, data in api_data.items():
                if isinstance(data, dict):
                    if 'backdrops' in data:
                        all_backdrops.extend(data['backdrops'])
                    if 'patterns' in data:
                        all_patterns.extend(data['patterns'])
                    if 'models' in data:
                        all_models.extend(data['models'])
            
            result = {
                "backdrops": all_backdrops,
                "patterns": all_patterns if all_patterns else None,
                "models": all_models if all_models else None
            }
            
            # Обновляем статистику
            await self.repository.update_endpoint_stat("get_attribute_volumes", "success", frequency_minutes=1440)
            
            return result
            
        except Exception as e:
            await self.repository.update_endpoint_stat("get_attribute_volumes", "error", str(e))
            logger.error(f"Failed to get attribute volumes: {e}")
            raise GiftAssetAPIException(f"Failed to get attribute volumes: {str(e)}")
    
    async def get_collections_metadata(self) -> List[Dict[str, Any]]:
        """Получить метаданные коллекций"""
        try:
            api_data = await gift_asset_service.get_collections_metadata()
            
            # Обновляем статистику
            await self.repository.update_endpoint_stat("get_collections_metadata", "success", frequency_minutes=1440)
            
            return api_data
            
        except Exception as e:
            await self.repository.update_endpoint_stat("get_collections_metadata", "error", str(e))
            logger.error(f"Failed to get collections metadata: {e}")
            raise GiftAssetAPIException(f"Failed to get collections metadata: {str(e)}")
    
    async def get_collection_offers(self, collection_name: str) -> Dict[str, Any]:
        """Получить офферы на коллекцию"""
        try:
            api_data = await gift_asset_service.get_collection_offers(collection_name)
            
            # Обновляем статистику
            await self.repository.update_endpoint_stat("get_collection_offers", "success", frequency_minutes=0)
            
            return api_data
            
        except Exception as e:
            await self.repository.update_endpoint_stat("get_collection_offers", "error", str(e))
            logger.error(f"Failed to get collection offers: {e}")
            raise GiftAssetAPIException(f"Failed to get collection offers: {str(e)}")
    
    async def get_update_stats(self) -> List[Dict[str, Any]]:
        """Получить статистику обновлений"""
        try:
            return await self.repository.get_update_stats()
        except Exception as e:
            logger.error(f"Failed to get update stats: {e}")
            raise GiftAssetCacheException(f"Failed to get update stats: {str(e)}")
    
    # Методы для принудительного обновления кеша
    async def refresh_price_list(self, models: bool = False, premarket: bool = False) -> Dict[str, Any]:
        """Принудительно обновить список цен"""
        return await self.get_gifts_price_list(models=models, premarket=premarket, force_refresh=True)
    
    async def refresh_collections_volumes(self) -> Dict[str, Any]:
        """Принудительно обновить объемы продаж коллекций"""
        return await self.get_collections_volumes(force_refresh=True)
    
    async def refresh_collections_emission(self) -> Dict[str, Any]:
        """Принудительно обновить данные об эмиссии коллекций"""
        return await self.get_collections_emission(force_refresh=True)
    
    async def refresh_collections_health_index(self) -> Dict[str, Any]:
        """Принудительно обновить индекс здоровья коллекций"""
        return await self.get_collections_health_index(force_refresh=True)
    
    async def refresh_total_market_cap(self) -> Dict[str, Any]:
        """Принудительно обновить общую рыночную капитализацию"""
        return await self.get_total_market_cap(force_refresh=True)
    
    async def refresh_providers_stats(self) -> Dict[str, Any]:
        """Принудительно обновить статистику провайдеров"""
        return await self.get_providers_stats(force_refresh=True)
    
    async def refresh_sales_history(self) -> List[Dict[str, Any]]:
        """Принудительно обновить историю продаж"""
        return await self.get_sales_history(force_refresh=True)
