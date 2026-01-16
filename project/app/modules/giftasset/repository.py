"""
Gift Asset репозиторий для работы с БД
"""
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, delete, and_, or_, desc, asc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.db.models.giftasset import (
    GiftAssetPriceList,
    GiftAssetVolume,
    GiftAssetEmission,
    GiftAssetHealthIndex,
    GiftAssetMarketCap,
    GiftAssetPriceHistory,
    GiftAssetProviderStats,
    GiftAssetSalesHistory,
    GiftAssetMetadata,
    GiftAssetUpdateStat
)
from app.modules.giftasset.service import gift_asset_service
from app.utils.logger import logger


class GiftAssetRepository:
    """Репозиторий для работы с Gift Asset данными"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # Price List методы
    async def get_price_list(self, include_models: bool = False) -> Dict[str, Any]:
        """Получить список цен из кеша"""
        query = select(GiftAssetPriceList)
        
        if not include_models:
            query = query.where(GiftAssetPriceList.model_name.is_(None))
        
        result = await self.session.execute(query)
        price_data = result.scalars().all()
        
        # Формируем ответ в нужном формате
        collection_floors = {}
        models_prices = []
        
        for item in price_data:
            if item.model_name is None:
                # Это floor коллекции
                collection_floors[item.collection_name] = {
                    "getgems": item.price_getgems,
                    "mrkt": item.price_mrkt,
                    "portals": item.price_portals,
                    "tonnel": item.price_tonnel,
                    "last_update": item.last_update
                }
            else:
                # Это цена модели
                models_prices.append({
                    "collection_name": item.collection_name,
                    "model_name": item.model_name,
                    "price_getgems": item.price_getgems,
                    "price_mrkt": item.price_mrkt,
                    "price_portals": item.price_portals,
                    "price_tonnel": item.price_tonnel,
                    "last_models_update": item.last_update
                })
        
        response = {"collection_floors": collection_floors}
        if include_models:
            response["models_prices"] = models_prices
            
        return response

    async def get_gifts_price_list_history(self) -> Dict[str, Any]:
        """Получить историю цен из API без записи в БД"""
        return await gift_asset_service.get_gifts_price_list_history()
    
    async def update_price_list(self, price_data: Dict[str, Any]):
        """Обновить список цен в кеше"""
        try:
            # Обновляем collection floors
            if "collection_floors" in price_data:
                for collection_name, floors in price_data["collection_floors"].items():
                    stmt = insert(GiftAssetPriceList).values(
                        collection_name=collection_name,
                        model_name=None,
                        price_getgems=floors.get("getgems"),
                        price_mrkt=floors.get("mrkt"),
                        price_portals=floors.get("portals"),
                        price_tonnel=floors.get("tonnel"),
                        last_update=datetime.utcnow()
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['collection_name', 'model_name'],
                        set_=dict(
                            price_getgems=stmt.excluded.price_getgems,
                            price_mrkt=stmt.excluded.price_mrkt,
                            price_portals=stmt.excluded.price_portals,
                            price_tonnel=stmt.excluded.price_tonnel,
                            last_update=stmt.excluded.last_update,
                            updated_at=datetime.utcnow()
                        )
                    )
                    await self.session.execute(stmt)
            
            # Обновляем models prices
            if "models_prices" in price_data:
                for model in price_data["models_prices"]:
                    stmt = insert(GiftAssetPriceList).values(
                        collection_name=model["collection_name"],
                        model_name=model["model_name"],
                        price_getgems=model.get("price_getgems"),
                        price_mrkt=model.get("price_mrkt"),
                        price_portals=model.get("price_portals"),
                        price_tonnel=model.get("price_tonnel"),
                        last_update=datetime.utcnow()
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['collection_name', 'model_name'],
                        set_=dict(
                            price_getgems=stmt.excluded.price_getgems,
                            price_mrkt=stmt.excluded.price_mrkt,
                            price_portals=stmt.excluded.price_portals,
                            price_tonnel=stmt.excluded.price_tonnel,
                            last_update=stmt.excluded.last_update,
                            updated_at=datetime.utcnow()
                        )
                    )
                    await self.session.execute(stmt)
            
            await self.session.commit()
            logger.info("Price list updated successfully")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update price list: {e}")
            raise
    
    # Volumes методы
    async def get_collections_volumes(self) -> Dict[str, Any]:
        """Получить объемы продаж коллекций"""
        today = date.today()
        query = select(GiftAssetVolume).where(GiftAssetVolume.sales_date == today)
        result = await self.session.execute(query)
        volumes = result.scalars().all()
        
        # Группируем по коллекциям и провайдерам
        collections = {}
        for volume in volumes:
            if volume.collection_name not in collections:
                collections[volume.collection_name] = {}
            
            collections[volume.collection_name][volume.provider] = {
                "hour_revenue": volume.hour_revenue,
                "hour_sales": volume.hour_sales,
                "total_revenue": volume.total_revenue,
                "total_sales": volume.total_sales,
                "peak_hour": volume.peak_hour.isoformat() if volume.peak_hour else None,
                "peak_hour_revenue_percent": volume.peak_hour_revenue_percent,
                "peak_hour_sales_percent": volume.peak_hour_sales_percent
            }
        
        return {"collections": collections}
    
    async def update_collections_volumes(self, volumes_data: Dict[str, Any]):
        """Обновить объемы продаж коллекций
        
        API возвращает формат: {provider: {collection: data}}
        Нужно преобразовать в: collection -> provider -> data
        """
        try:
            today = date.today()
            
            # Проверяем формат данных и преобразуем если нужно
            # Если первый уровень ключей - это провайдеры (mrkt, portals, tonnel, getgems)
            first_key = next(iter(volumes_data.keys())) if volumes_data else None
            if first_key in ['mrkt', 'portals', 'tonnel', 'getgems']:
                # Формат: {provider: {collection: data}} - нужно инвертировать
                logger.info("Detected provider->collection format, inverting...")
                inverted_data = {}
                for provider, collections in volumes_data.items():
                    for collection_name, data in collections.items():
                        if collection_name not in inverted_data:
                            inverted_data[collection_name] = {}
                        inverted_data[collection_name][provider] = data
                volumes_data = inverted_data
            
            # Теперь volumes_data в формате {collection: {provider: data}}
            for collection_name, providers in volumes_data.items():
                for provider, data in providers.items():
                    peak_hour = None
                    if data.get("peak_hour"):
                        try:
                            peak_hour = datetime.fromisoformat(data["peak_hour"].replace("Z", "+00:00"))
                        except:
                            pass
                    
                    stmt = insert(GiftAssetVolume).values(
                        collection_name=collection_name,
                        provider=provider,
                        hour_revenue=data.get("hour_revenue", 0.0),
                        hour_sales=data.get("hour_sales", 0),
                        total_revenue=data.get("total_revenue", 0.0),
                        total_sales=data.get("total_sales", 0),
                        peak_hour=peak_hour,
                        peak_hour_revenue_percent=data.get("peak_hour_revenue_percent", 0.0),
                        peak_hour_sales_percent=data.get("peak_hour_sales_percent", 0.0),
                        sales_date=today
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['collection_name', 'provider', 'sales_date'],
                        set_=dict(
                            hour_revenue=stmt.excluded.hour_revenue,
                            hour_sales=stmt.excluded.hour_sales,
                            total_revenue=stmt.excluded.total_revenue,
                            total_sales=stmt.excluded.total_sales,
                            peak_hour=stmt.excluded.peak_hour,
                            peak_hour_revenue_percent=stmt.excluded.peak_hour_revenue_percent,
                            peak_hour_sales_percent=stmt.excluded.peak_hour_sales_percent,
                            updated_at=datetime.utcnow()
                        )
                    )
                    await self.session.execute(stmt)
            
            await self.session.commit()
            logger.info("Collections volumes updated successfully")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update collections volumes: {e}")
            raise
    
    # Emission методы
    async def get_collections_emission(self) -> Dict[str, Any]:
        """Получить данные об эмиссии коллекций
        
        Возвращает данные в формате API с providers и providers_percentages как dicts
        """
        query = select(GiftAssetEmission)
        result = await self.session.execute(query)
        emissions = result.scalars().all()
        
        collections = {}
        for emission in emissions:
            collections[emission.collection_name] = {
                "emission": emission.emission,
                "deleted": emission.deleted,
                "hidden": emission.hidden,
                "refunded": emission.refunded,
                "upgraded": emission.upgraded,
                "unique_owners": emission.unique_owners,
                "top_30_whales_hold": emission.top_30_whales_hold,
                # Возвращаем в формате API - как dicts
                "providers": {
                    "mrkt": emission.mrkt_count,
                    "portals": emission.portals_count,
                    "tonnel": emission.tonnel_count
                },
                "providers_percentages": {
                    "mrkt": emission.mrkt_percentage,
                    "portals": emission.portals_percentage,
                    "tonnel": emission.tonnel_percentage
                }
            }
        
        return {"collections": collections}
    
    async def update_collections_emission(self, emission_data: Dict[str, Any]):
        """Обновить данные об эмиссии коллекций"""
        try:
            for collection_name, data in emission_data.items():
                # Извлекаем данные из providers и providers_percentages dicts
                providers = data.get("providers", {})
                providers_percentages = data.get("providers_percentages", {})
                
                stmt = insert(GiftAssetEmission).values(
                    collection_name=collection_name,
                    emission=data.get("emission", 0),
                    deleted=data.get("deleted", 0),
                    hidden=data.get("hidden", 0),
                    refunded=data.get("refunded", 0),
                    upgraded=data.get("upgraded", 0),
                    unique_owners=data.get("unique_owners", 0),
                    top_30_whales_hold=data.get("top_30_whales_hold", 0),
                    mrkt_count=providers.get("mrkt", 0),
                    portals_count=providers.get("portals", 0),
                    tonnel_count=providers.get("tonnel", 0),
                    mrkt_percentage=providers_percentages.get("mrkt", 0.0),
                    portals_percentage=providers_percentages.get("portals", 0.0),
                    tonnel_percentage=providers_percentages.get("tonnel", 0.0)
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=['collection_name'],
                    set_=dict(
                        emission=stmt.excluded.emission,
                        deleted=stmt.excluded.deleted,
                        hidden=stmt.excluded.hidden,
                        refunded=stmt.excluded.refunded,
                        upgraded=stmt.excluded.upgraded,
                        unique_owners=stmt.excluded.unique_owners,
                        top_30_whales_hold=stmt.excluded.top_30_whales_hold,
                        mrkt_count=stmt.excluded.mrkt_count,
                        portals_count=stmt.excluded.portals_count,
                        tonnel_count=stmt.excluded.tonnel_count,
                        mrkt_percentage=stmt.excluded.mrkt_percentage,
                        portals_percentage=stmt.excluded.portals_percentage,
                        tonnel_percentage=stmt.excluded.tonnel_percentage,
                        updated_at=datetime.utcnow()
                    )
                )
                await self.session.execute(stmt)
            
            await self.session.commit()
            logger.info("Collections emission updated successfully")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update collections emission: {e}")
            raise
    
    # Health Index методы
    async def get_collections_health_index(self) -> Dict[str, Any]:
        """Получить индекс здоровья коллекций"""
        query = select(GiftAssetHealthIndex)
        result = await self.session.execute(query)
        health_indices = result.scalars().all()
        
        collections = {}
        for health in health_indices:
            collections[health.collection_name] = {
                "health_index": health.health_index,
                "liquidity": health.liquidity,
                "market_cap": health.market_cap,
                "whale_concentration": health.whale_concentration,
                "norm_liquidity": health.norm_liquidity,
                "norm_market_cap": health.norm_market_cap,
                "norm_whale_concentration": health.norm_whale_concentration
            }
        
        return {"collections": collections}
    
    async def update_collections_health_index(self, health_data: Dict[str, Any]):
        """Обновить индекс здоровья коллекций"""
        try:
            for collection_name, data in health_data.items():
                stmt = insert(GiftAssetHealthIndex).values(
                    collection_name=collection_name,
                    health_index=data.get("health_index", 0.0),
                    liquidity=data.get("liquidity", 0),
                    market_cap=data.get("market_cap", 0.0),
                    whale_concentration=data.get("whale_concentration", 0.0),
                    norm_liquidity=data.get("norm_liquidity", 0.0),
                    norm_market_cap=data.get("norm_market_cap", 0.0),
                    norm_whale_concentration=data.get("norm_whale_concentration", 0.0)
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=['collection_name'],
                    set_=dict(
                        health_index=stmt.excluded.health_index,
                        liquidity=stmt.excluded.liquidity,
                        market_cap=stmt.excluded.market_cap,
                        whale_concentration=stmt.excluded.whale_concentration,
                        norm_liquidity=stmt.excluded.norm_liquidity,
                        norm_market_cap=stmt.excluded.norm_market_cap,
                        norm_whale_concentration=stmt.excluded.norm_whale_concentration,
                        updated_at=datetime.utcnow()
                    )
                )
                await self.session.execute(stmt)
            
            await self.session.commit()
            logger.info("Collections health index updated successfully")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update collections health index: {e}")
            raise
    
    # Market Cap методы
    async def get_total_market_cap(self) -> Dict[str, Any]:
        """Получить общую рыночную капитализацию"""
        query = select(GiftAssetMarketCap).order_by(desc(GiftAssetMarketCap.record_datetime)).limit(1)
        result = await self.session.execute(query)
        market_cap = result.scalar_one_or_none()
        
        if market_cap:
            return {
                "total_market_cap": market_cap.total_market_cap,
                "collections_count": market_cap.collections_count
            }
        
        return {"total_market_cap": 0.0, "collections_count": 0}
    
    async def get_market_cap_history(self, period: str = "7d", include_previous: bool = False) -> Dict[str, Any]:
        """Получить историю капитализации"""
        # Определяем период
        now = datetime.utcnow()
        if period == "24h":
            start_date = now - timedelta(hours=24)
            if include_previous:
                start_date = now - timedelta(hours=48)
        elif period == "7d":
            start_date = now - timedelta(days=7)
            if include_previous:
                start_date = now - timedelta(days=14)
        elif period == "30d":
            start_date = now - timedelta(days=30)
            if include_previous:
                start_date = now - timedelta(days=60)
        elif period == "90d":
            start_date = now - timedelta(days=90)
            if include_previous:
                start_date = now - timedelta(days=180)
        else:
            start_date = now - timedelta(days=7)
        
        query = select(GiftAssetMarketCap).where(
            GiftAssetMarketCap.record_datetime >= start_date
        ).order_by(GiftAssetMarketCap.record_datetime)
        
        result = await self.session.execute(query)
        history_data = result.scalars().all()
        
        history = []
        for item in history_data:
            history.append({
                "date": item.record_date.isoformat(),
                "datetime": item.record_datetime.isoformat(),
                "total_market_cap": item.total_market_cap,
                "collections_count": item.collections_count
            })
        
        return {
            "period": period,
            "history": history,
            "total_records": len(history)
        }
    
    async def save_market_cap(self, total_market_cap: float, collections_count: int):
        """Сохранить данные о капитализации"""
        try:
            market_cap = GiftAssetMarketCap(
                total_market_cap=total_market_cap,
                collections_count=collections_count,
                record_date=date.today(),
                record_datetime=datetime.utcnow()
            )
            self.session.add(market_cap)
            await self.session.commit()
            logger.info("Market cap saved successfully")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to save market cap: {e}")
            raise
    
    # Provider Stats методы
    async def get_providers_stats(self) -> Dict[str, Any]:
        """Получить статистику провайдеров"""
        query = select(GiftAssetProviderStats)
        result = await self.session.execute(query)
        stats = result.scalars().all()
        
        providers = []
        for stat in stats:
            providers.append({
                "provider": stat.provider,
                "hour_revenue": stat.hour_revenue,
                "hour_sales": stat.hour_sales,
                "peak_hour": stat.peak_hour,
                "peak_hour_revenue_percent": stat.peak_hour_revenue_percent,
                "peak_hour_sales_percent": stat.peak_hour_sales_percent,
                "total_revenue": stat.total_revenue,
                "total_sales": stat.total_sales,
                "fee": stat.fee
            })
        
        return {"providers": providers}
    
    async def update_providers_stats(self, providers_data: List[Dict[str, Any]]):
        """Обновить статистику провайдеров"""
        try:
            for provider_data in providers_data:
                stmt = insert(GiftAssetProviderStats).values(
                    provider=provider_data["provider"],
                    hour_revenue=provider_data.get("hour_revenue", 0.0),
                    hour_sales=provider_data.get("hour_sales", 0),
                    total_revenue=provider_data.get("total_revenue", 0.0),
                    total_sales=provider_data.get("total_sales", 0),
                    peak_hour=provider_data.get("peak_hour"),
                    peak_hour_revenue_percent=provider_data.get("peak_hour_revenue_percent", 0.0),
                    peak_hour_sales_percent=provider_data.get("peak_hour_sales_percent", 0.0),
                    fee=provider_data.get("fee", 0.0)
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=['provider'],
                    set_=dict(
                        hour_revenue=stmt.excluded.hour_revenue,
                        hour_sales=stmt.excluded.hour_sales,
                        total_revenue=stmt.excluded.total_revenue,
                        total_sales=stmt.excluded.total_sales,
                        peak_hour=stmt.excluded.peak_hour,
                        peak_hour_revenue_percent=stmt.excluded.peak_hour_revenue_percent,
                        peak_hour_sales_percent=stmt.excluded.peak_hour_sales_percent,
                        fee=stmt.excluded.fee,
                        updated_at=datetime.utcnow()
                    )
                )
                await self.session.execute(stmt)
            
            await self.session.commit()
            logger.info("Providers stats updated successfully")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update providers stats: {e}")
            raise
    
    # Sales History методы
    async def get_sales_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить историю продаж"""
        query = select(GiftAssetSalesHistory).order_by(
            desc(GiftAssetSalesHistory.sale_datetime)
        ).limit(limit)
        
        result = await self.session.execute(query)
        sales = result.scalars().all()
        
        history = []
        for sale in sales:
            history.append({
                "collection_name": sale.collection_name,
                "price": sale.price,
                "provider": sale.provider,
                "telegram_gift_id": sale.telegram_gift_id,
                "telegram_gift_name": sale.telegram_gift_name,
                "telegram_gift_number": sale.telegram_gift_number,
                "unix_time": sale.unix_time
            })
        
        return history
    
    async def save_sales_history(self, sales_data: List[Dict[str, Any]]):
        """Сохранить историю продаж"""
        try:
            for sale in sales_data:
                # Конвертируем unix timestamp в datetime
                sale_datetime = datetime.fromtimestamp(sale["unix_time"])
                
                stmt = insert(GiftAssetSalesHistory).values(
                    collection_name=sale["collection_name"],
                    provider=sale["provider"],
                    price=sale["price"],
                    telegram_gift_id=int(sale["telegram_gift_id"]),
                    telegram_gift_name=sale["telegram_gift_name"],
                    telegram_gift_number=sale["telegram_gift_number"],
                    unix_time=sale["unix_time"],
                    sale_datetime=sale_datetime
                )
                # Используем ON CONFLICT DO NOTHING чтобы избежать дублей
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['telegram_gift_id', 'unix_time']
                )
                await self.session.execute(stmt)
            
            await self.session.commit()
            logger.info(f"Saved {len(sales_data)} sales history records")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to save sales history: {e}")
            raise
    
    # Update Stats методы
    async def update_endpoint_stat(self, endpoint: str, status: str = "success", 
                                 error_message: Optional[str] = None, 
                                 frequency_minutes: int = 30):
        """Обновить статистику обновления endpoint"""
        try:
            stmt = insert(GiftAssetUpdateStat).values(
                endpoint=endpoint,
                last_update=datetime.utcnow(),
                update_frequency_minutes=frequency_minutes,
                status=status,
                error_message=error_message
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=['endpoint'],
                set_=dict(
                    last_update=stmt.excluded.last_update,
                    status=stmt.excluded.status,
                    error_message=stmt.excluded.error_message,
                    updated_at=datetime.utcnow()
                )
            )
            await self.session.execute(stmt)
            await self.session.commit()
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update endpoint stat: {e}")
            raise
    
    async def get_update_stats(self) -> List[Dict[str, Any]]:
        """Получить статистику обновлений"""
        query = select(GiftAssetUpdateStat).order_by(GiftAssetUpdateStat.endpoint)
        result = await self.session.execute(query)
        stats = result.scalars().all()
        
        updates = []
        for stat in stats:
            updates.append({
                "endpoint": stat.endpoint,
                "last_update": stat.last_update,
                "update_frequency_minutes": stat.update_frequency_minutes,
                "status": stat.status,
                "error_message": stat.error_message
            })
        
        return updates
