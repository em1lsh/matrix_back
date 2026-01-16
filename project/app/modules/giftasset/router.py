"""
Gift Asset API роутеры
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.api.auth import get_current_user_optional
from app.modules.giftasset.use_cases import GiftAssetUseCases
from app.modules.giftasset.schemas import (
    GiftAssetPriceListResponse,
    GiftsPriceListHistoryResponse,
    CollectionsVolumesResponse,
    CollectionsEmissionResponse,
    CollectionsHealthIndexResponse,
    TotalMarketCapResponse,
    MarketCapHistoryResponse,
    CollectionPriceHistoryResponse,
    CollectionMarketCapHistoryResponse,
    ProvidersStatsResponse,
    SalesHistoryResponse,
    UserCollectionsResponse,
    AttributeVolumesResponse,
    CollectionsMetadataResponse,
    UpdateStatsResponse
)

router = APIRouter(prefix="/giftasset", tags=["Gift Asset"])


@router.get("/get_gifts_price_list", response_model=GiftAssetPriceListResponse)
async def get_gifts_price_list(
    models: bool = Query(False, description="Include models prices"),
    premarket: bool = Query(False, description="Filter premarket collections"),
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Получить список цен коллекций и моделей из БД
    
    Данные обновляются автоматически каждые 30 минут фоновой задачей
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.get_gifts_price_list(models=models, premarket=premarket)
    return result


@router.post("/get_gifts_price_list/refresh", response_model=GiftAssetPriceListResponse)
async def refresh_gifts_price_list(
    models: bool = Query(False, description="Include models prices"),
    premarket: bool = Query(False, description="Filter premarket collections"),
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Принудительно обновить список цен коллекций и моделей
    
    Запрашивает свежие данные с giftasset.pro API и сохраняет в БД.
    Полезно для ручного обновления данных без ожидания следующего автоматического обновления.
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.refresh_price_list(models=models, premarket=premarket)
    return result


@router.get("/get_gifts_price_list_history", response_model=GiftsPriceListHistoryResponse)
async def get_gifts_price_list_history(
    collection_name: str = Query(..., description="Collection name"),
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Получить историю цен подарков по коллекции
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.get_gifts_price_list_history(collection_name=collection_name)
    return result


@router.get("/collections-volumes", response_model=CollectionsVolumesResponse)
async def get_collections_volumes(
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Получить объемы продаж коллекций за 24 часа из БД
    
    Возвращает агрегированные данные по всем коллекциям:
    - total_revenue: сумма по portals + tonnel + mrkt (без getgems)
    - total_sales: сумма по portals + tonnel + mrkt (без getgems)
    - by_market: данные отдельно по каждому маркету
    
    Данные обновляются автоматически каждый час фоновой задачей.
    Для ручного обновления используйте POST /giftasset/collections-volumes/refresh
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.get_collections_volumes()
    return result


@router.post("/collections-volumes/refresh", response_model=CollectionsVolumesResponse)
async def refresh_collections_volumes(
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Принудительно обновить объемы продаж коллекций
    
    Запрашивает свежие данные с giftasset.pro API и сохраняет в БД.
    Полезно для ручного обновления данных без ожидания следующего автоматического обновления.
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.refresh_collections_volumes()
    return result


@router.get("/collections-emission", response_model=CollectionsEmissionResponse)
async def get_collections_emission(
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Получить данные об эмиссии коллекций из БД
    
    Возвращает данные по всем коллекциям:
    - emission: общее количество выпущенных подарков
    - deleted, hidden, refunded, upgraded: статусы подарков
    - unique_owners: количество уникальных владельцев
    - top_30_whales_hold: количество подарков у топ-30 китов
    - mrkt_count, portals_count, tonnel_count: количество на маркетплейсах (без getgems)
    - mrkt_percentage, portals_percentage, tonnel_percentage: проценты распределения (сумма = 100%)
    
    Данные обновляются автоматически раз в сутки фоновой задачей.
    Для ручного обновления используйте POST /giftasset/collections-emission/refresh
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.get_collections_emission()
    return result


@router.post("/collections-emission/refresh", response_model=CollectionsEmissionResponse)
async def refresh_collections_emission(
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Принудительно обновить данные об эмиссии коллекций
    
    Запрашивает свежие данные с giftasset.pro API и сохраняет в БД.
    Полезно для ручного обновления данных без ожидания следующего автоматического обновления.
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.refresh_collections_emission()
    return result


@router.get("/collections-health-index", response_model=CollectionsHealthIndexResponse)
async def get_collections_health_index(
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Получить данные об индексе здоровья коллекций из БД
    
    Возвращает данные по всем коллекциям:
    - health_index: общий индекс здоровья коллекции (чем выше, тем лучше)
    - liquidity: ликвидность (количество подарков на маркетах)
    - market_cap: рыночная капитализация (пересчитывается как upgraded * min_floor при сохранении в БД)
    - norm_liquidity, norm_market_cap, norm_whale_concentration: нормализованные метрики (0-1)
    - whale_concentration: концентрация китов (процент подарков у крупных держателей)
    
    Данные обновляются автоматически раз в сутки фоновой задачей.
    Для ручного обновления используйте POST /giftasset/collections-health-index/refresh
    
    Примечание: market_cap автоматически пересчитывается при сохранении в БД на основе 
    данных эмиссии (upgraded) и минимального флора среди трех маркетов (mrkt, portals, tonnel).
    Если данные еще не обновлены, выполняется пересчет на лету.
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.get_collections_health_index()
    return result


@router.post("/collections-health-index/refresh", response_model=CollectionsHealthIndexResponse)
async def refresh_collections_health_index(
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Принудительно обновить данные об индексе здоровья коллекций
    
    Запрашивает свежие данные с giftasset.pro API и сохраняет в БД.
    Полезно для ручного обновления данных без ожидания следующего автоматического обновления.
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.refresh_collections_health_index()
    return result


@router.get("/total-market-cap", response_model=TotalMarketCapResponse)
async def get_total_market_cap(
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Получить общую рыночную капитализацию всего рынка
    
    Возвращает сумму всех market_cap всех коллекций.
    Капитализация рассчитывается как: upgraded * min(price_mrkt, price_portals, price_tonnel)
    
    Данные обновляются автоматически раз в сутки фоновой задачей.
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.get_total_market_cap()
    return result


@router.get("/total-market-cap/history", response_model=MarketCapHistoryResponse)
async def get_total_market_cap_history(
    period: str = Query("7d", description="Период: '24h', '7d', '30d' или '90d'"),
    include_previous: bool = Query(False, description="Включить данные за предыдущий период для сравнения"),
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Получить историю общей рыночной капитализации для построения графиков
    
    Возвращает исторические данные по капитализации за указанный период.
    Данные сохраняются автоматически каждый час фоновой задачей.
    
    Для периодов 7d, 30d, 90d данные группируются по дням (нормализуются до начала дня).
    Для периода 24h возвращаются данные по часам.
    
    Args:
        period: Период ('24h', '7d', '30d', '90d')
        include_previous: Если True, вернет данные за удвоенный период (для сравнения с предыдущим)
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.get_total_market_cap_history(period=period, include_previous=include_previous)
    return result


@router.get("/providers-stats", response_model=ProvidersStatsResponse)
async def get_providers_stats(
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Получить объединенную статистику по провайдерам из БД
    
    Возвращает данные по всем провайдерам (mrkt, portals, tonnel, без getgems):
    - Данные из volumes (обновляются раз в 5 минут):
      * hour_revenue, hour_sales: объемы за последний час
      * peak_hour: час пик
      * peak_hour_revenue_percent, peak_hour_sales_percent: проценты пика
      * total_revenue, total_sales: общие объемы за 24 часа
    - Данные из fee (обновляются раз в сутки):
      * fee: комиссия провайдера (в процентах)
    
    Данные обновляются автоматически фоновыми задачами.
    Для ручного обновления используйте POST /giftasset/providers-stats/refresh
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.get_providers_stats()
    return result


@router.post("/providers-stats/refresh", response_model=ProvidersStatsResponse)
async def refresh_providers_stats(
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Принудительно обновить статистику провайдеров
    
    Запрашивает свежие данные с giftasset.pro API (volumes + fee) и сохраняет в БД.
    Полезно для ручного обновления данных без ожидания следующего автоматического обновления.
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.refresh_providers_stats()
    return result


@router.get("/sales-history", response_model=SalesHistoryResponse)
async def get_sales_history(
    limit: int = Query(100, description="Количество записей для возврата"),
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Получить историю продаж всех провайдеров
    
    Возвращает последние продажи с всех маркетплейсов (mrkt, portals, tonnel).
    Данные обновляются автоматически каждые 5 минут фоновой задачей.
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.get_sales_history(limit=limit)
    return {"sales": result}


@router.post("/sales-history/refresh", response_model=SalesHistoryResponse)
async def refresh_sales_history(
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Принудительно обновить историю продаж
    
    Запрашивает свежие данные с giftasset.pro API и сохраняет в БД.
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.refresh_sales_history()
    return {"sales": result}


@router.post("/user-collections", response_model=UserCollectionsResponse)
async def get_user_collections(
    username: str = Query(..., description="Telegram username"),
    include: Optional[List[str]] = Query(None, description="Только указанные коллекции"),
    exclude: Optional[List[str]] = Query(None, description="Все кроме указанных коллекций"),
    limit: Optional[int] = Query(None, description="Лимит возвращаемых подарков"),
    offset: Optional[int] = Query(None, description="Смещение возвращаемых подарков"),
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Получить все коллекции пользователя по Telegram username
    
    Возвращает список коллекций пользователя с количеством подарков в каждой.
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.get_user_collections(
        username=username,
        include=include,
        exclude=exclude,
        limit=limit,
        offset=offset
    )
    return {"collections": result}


@router.get("/attribute-volumes", response_model=AttributeVolumesResponse)
async def get_attribute_volumes(
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Получить топ объемов продаж отдельных атрибутов за день
    
    Возвращает данные по объемам продаж различных атрибутов (фоны, паттерны, модели).
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.get_attribute_volumes()
    return result


@router.get("/collections-metadata", response_model=CollectionsMetadataResponse)
async def get_collections_metadata(
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Получить метаданные коллекций
    
    Возвращает информацию о доступных атрибутах для каждой коллекции.
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.get_collections_metadata()
    return {"collections": result}


@router.post("/collection-offers")
async def get_collection_offers(
    collection_name: str = Query(..., description="Название коллекции"),
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Получить офферы на покупку коллекции
    
    Возвращает активные предложения на покупку подарков из указанной коллекции.
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.get_collection_offers(collection_name=collection_name)
    return result


@router.get("/update-stats", response_model=UpdateStatsResponse)
async def get_update_stats(
    session: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Получить статистику обновлений данных
    
    Показывает когда последний раз обновлялись различные типы данных,
    частоту обновлений и статус последнего обновления.
    """
    use_cases = GiftAssetUseCases(session)
    result = await use_cases.get_update_stats()
    return {"updates": result}


# WebSocket endpoint info (документация)
@router.get("/ws/sales-history/info")
async def websocket_sales_history_info():
    """
    Информация о WebSocket endpoint для истории продаж
    
    **WebSocket URL:** `wss://api.yourdomain.com/giftasset/ws/sales-history?token=YOUR_TOKEN`
    
    **Параметры:**
    - `token` (query): Токен авторизации (обязательно)
    
    **Как использовать:**
    1. Получите токен через `/users/auth`
    2. Подключитесь к WebSocket с токеном
    3. Получайте обновления в реальном времени каждые 5 секунд
    
    **Формат сообщений:**
    ```json
    {
      "type": "sales_history_update",
      "data": {
        "mrkt": [...],
        "portals": [...],
        "tonnel": [...],
        "last_update": "2025-01-XX..."
      }
    }
    ```
    
    **Пример подключения (JavaScript):**
    ```javascript
    const ws = new WebSocket('wss://api.yourdomain.com/giftasset/ws/sales-history?token=YOUR_TOKEN');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Обновление:', data);
    };
    ```
    """
    return {
        "message": "WebSocket endpoint для истории продаж в реальном времени",
        "url": "wss://api.yourdomain.com/giftasset/ws/sales-history?token=YOUR_TOKEN",
        "update_frequency": "5 seconds",
        "authentication": "required"
    }
