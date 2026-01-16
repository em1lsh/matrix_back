"""
Gift Asset API схемы ответов
"""
from datetime import datetime, date
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class CollectionFloorResponse(BaseModel):
    """Цены коллекции по маркетплейсам"""
    getgems: Optional[float] = Field(None, description="Floor price on GetGems")
    mrkt: Optional[float] = Field(None, description="Floor price on MRKT")
    portals: Optional[float] = Field(None, description="Floor price on Portals")
    tonnel: Optional[float] = Field(None, description="Floor price on Tonnel")
    last_update: Optional[datetime] = Field(None, description="Last update timestamp")


class ModelPriceResponse(BaseModel):
    """Цены модели по маркетплейсам"""
    collection_name: str = Field(..., description="Collection name")
    model_name: str = Field(..., description="Model name")
    price_getgems: Optional[float] = Field(None, description="Price on GetGems")
    price_mrkt: Optional[float] = Field(None, description="Price on MRKT")
    price_portals: Optional[float] = Field(None, description="Price on Portals")
    price_tonnel: Optional[float] = Field(None, description="Price on Tonnel")
    last_models_update: Optional[datetime] = Field(None, description="Last update timestamp")


class GiftAssetPriceListResponse(BaseModel):
    """Ответ API со списком цен"""
    collection_floors: Dict[str, CollectionFloorResponse] = Field(..., description="Collection floor prices")
    models_prices: Optional[List[ModelPriceResponse]] = Field(None, description="Model prices (if requested)")


class CollectionVolumeData(BaseModel):
    """Данные об объеме продаж коллекции с одного маркетплейса"""
    hour_revenue: float = Field(..., description="Revenue for the last hour")
    hour_sales: int = Field(..., description="Number of sales for the last hour")
    total_revenue: float = Field(..., description="Total revenue for 24h")
    total_sales: int = Field(..., description="Total number of sales for 24h")
    peak_hour: Optional[str] = Field(None, description="Peak hour timestamp")
    peak_hour_revenue_percent: float = Field(..., description="Peak hour revenue percentage")
    peak_hour_sales_percent: float = Field(..., description="Peak hour sales percentage")


class CollectionsVolumesResponse(BaseModel):
    """Объемы продаж коллекций"""
    collections: Dict[str, Dict[str, CollectionVolumeData]] = Field(
        ..., 
        description="Collections volumes by provider"
    )


class CollectionEmissionData(BaseModel):
    """Данные об эмиссии одной коллекции"""
    emission: int = Field(..., description="Total emission")
    deleted: int = Field(..., description="Deleted gifts")
    hidden: int = Field(..., description="Hidden gifts")
    refunded: int = Field(..., description="Refunded gifts")
    upgraded: int = Field(..., description="Upgraded gifts")
    unique_owners: int = Field(..., description="Number of unique owners")
    top_30_whales_hold: int = Field(..., description="Gifts held by top 30 whales")
    providers: Dict[str, int] = Field(..., description="Provider counts (getgems, mrkt, portals, tonnel)")
    providers_percentages: Dict[str, float] = Field(..., description="Provider percentages")
    
    # Computed properties that return actual values for DB storage
    def get_mrkt_count(self) -> int:
        return self.providers.get('mrkt', 0)
    
    def get_portals_count(self) -> int:
        return self.providers.get('portals', 0)
    
    def get_tonnel_count(self) -> int:
        return self.providers.get('tonnel', 0)
    
    def get_mrkt_percentage(self) -> float:
        return self.providers_percentages.get('mrkt', 0.0)
    
    def get_portals_percentage(self) -> float:
        return self.providers_percentages.get('portals', 0.0)
    
    def get_tonnel_percentage(self) -> float:
        return self.providers_percentages.get('tonnel', 0.0)


class CollectionsEmissionResponse(BaseModel):
    """Ответ API с данными об эмиссии коллекций"""
    collections: Dict[str, CollectionEmissionData] = Field(..., description="Collections emission data")


class CollectionHealthIndexData(BaseModel):
    """Данные об индексе здоровья одной коллекции"""
    health_index: float = Field(..., description="Overall health index")
    liquidity: int = Field(..., description="Liquidity (gifts on markets)")
    market_cap: float = Field(..., description="Market capitalization")
    whale_concentration: float = Field(..., description="Whale concentration percentage")
    norm_liquidity: float = Field(..., description="Normalized liquidity (0-1)")
    norm_market_cap: float = Field(..., description="Normalized market cap (0-1)")
    norm_whale_concentration: float = Field(..., description="Normalized whale concentration (0-1)")


class CollectionsHealthIndexResponse(BaseModel):
    """Ответ API с данными об индексе здоровья коллекций"""
    collections: Dict[str, CollectionHealthIndexData] = Field(..., description="Collections health index data")


class TotalMarketCapResponse(BaseModel):
    """Общая рыночная капитализация"""
    total_market_cap: float = Field(..., description="Total market capitalization")
    collections_count: int = Field(..., description="Number of collections")


class MarketCapHistoryItem(BaseModel):
    """Одна запись истории капитализации"""
    date: str = Field(..., description="Date")
    datetime: Optional[str] = Field(None, description="Datetime")
    total_market_cap: float = Field(..., description="Total market cap")
    collections_count: int = Field(..., description="Collections count")


class MarketCapHistoryResponse(BaseModel):
    """История капитализации"""
    period: str = Field(..., description="Period")
    history: List[MarketCapHistoryItem] = Field(..., description="History data")
    total_records: int = Field(..., description="Total records count")


class CollectionPriceHistoryItem(BaseModel):
    """Одна запись истории цены коллекции"""
    provider: str = Field(..., description="Provider name")
    period_type: str = Field(..., description="Period type")
    price_date: str = Field(..., description="Price date")
    price: float = Field(..., description="Price")


class CollectionPriceHistoryResponse(BaseModel):
    """История цен коллекции"""
    collection_name: str = Field(..., description="Collection name")
    history: List[CollectionPriceHistoryItem] = Field(..., description="Price history")
    total_records: int = Field(..., description="Total records count")


class CollectionMarketCapHistoryItem(BaseModel):
    """Одна запись истории капитализации коллекции"""
    date: str = Field(..., description="Date")
    datetime: Optional[str] = Field(None, description="Datetime")
    market_cap: float = Field(..., description="Market cap")
    min_floor: float = Field(..., description="Minimum floor price")
    upgraded: int = Field(..., description="Upgraded count")


class CollectionMarketCapHistoryResponse(BaseModel):
    """История капитализации коллекции"""
    collection_name: str = Field(..., description="Collection name")
    period: str = Field(..., description="Period")
    history: List[CollectionMarketCapHistoryItem] = Field(..., description="Market cap history")
    total_records: int = Field(..., description="Total records count")


class ProviderStatsData(BaseModel):
    """Статистика одного провайдера"""
    provider: str = Field(..., description="Provider name")
    hour_revenue: float = Field(..., description="Hour revenue")
    hour_sales: int = Field(..., description="Hour sales")
    peak_hour: Optional[str] = Field(None, description="Peak hour")
    peak_hour_revenue_percent: float = Field(..., description="Peak hour revenue percent")
    peak_hour_sales_percent: float = Field(..., description="Peak hour sales percent")
    total_revenue: float = Field(..., description="Total revenue")
    total_sales: int = Field(..., description="Total sales")
    fee: float = Field(..., description="Provider fee")


class ProvidersStatsResponse(BaseModel):
    """Статистика всех провайдеров"""
    providers: List[ProviderStatsData] = Field(..., description="Providers statistics")


class SalesHistoryItem(BaseModel):
    """Одна запись истории продаж"""
    collection_name: str = Field(..., description="Collection name")
    price: float = Field(..., description="Sale price")
    provider: str = Field(..., description="Provider name")
    telegram_gift_id: int = Field(..., description="Telegram gift ID")
    telegram_gift_name: str = Field(..., description="Telegram gift name")
    telegram_gift_number: int = Field(..., description="Telegram gift number")
    unix_time: int = Field(..., description="Unix timestamp")


class SalesHistoryResponse(BaseModel):
    """История продаж"""
    sales: List[SalesHistoryItem] = Field(..., description="Sales history")


class UserCollectionItem(BaseModel):
    """Коллекция пользователя"""
    collection_name: str = Field(..., description="Collection name")
    count: int = Field(..., description="Number of gifts in collection")


class UserCollectionsResponse(BaseModel):
    """Коллекции пользователя"""
    collections: List[UserCollectionItem] = Field(..., description="User collections")


class AttributeVolumeItem(BaseModel):
    """Объем продаж атрибута"""
    collection_name: str = Field(..., description="Collection name")
    name: str = Field(..., description="Attribute name")
    sales_count: int = Field(..., description="Number of sales")
    sales_sum: str = Field(..., description="Total sales amount")


class AttributeVolumesResponse(BaseModel):
    """Объемы продаж атрибутов"""
    backdrops: List[AttributeVolumeItem] = Field(..., description="Backdrop volumes")
    patterns: Optional[List[AttributeVolumeItem]] = Field(None, description="Pattern volumes")
    models: Optional[List[AttributeVolumeItem]] = Field(None, description="Model volumes")


class CollectionMetadata(BaseModel):
    """Метаданные коллекции"""
    collection_name: str = Field(..., description="Collection name")
    telegram_id: Optional[Union[str, int]] = Field(None, description="Telegram collection ID")
    backdrops: Optional[List[str]] = Field(None, description="Available backdrops")
    patterns: Optional[List[str]] = Field(None, description="Available patterns")
    models: Optional[List[str]] = Field(None, description="Available models")


class CollectionsMetadataResponse(BaseModel):
    """Метаданные коллекций"""
    collections: List[CollectionMetadata] = Field(..., description="Collections metadata")


class UpdateStatItem(BaseModel):
    """Статистика обновления"""
    endpoint: str = Field(..., description="API endpoint")
    last_update: datetime = Field(..., description="Last update time")
    update_frequency_minutes: int = Field(..., description="Update frequency in minutes")
    status: str = Field(..., description="Update status")
    error_message: Optional[str] = Field(None, description="Error message if any")


class UpdateStatsResponse(BaseModel):
    """Статистика обновлений"""
    updates: List[UpdateStatItem] = Field(..., description="Update statistics")


# WebSocket схемы
class WebSocketSalesUpdate(BaseModel):
    """WebSocket обновление истории продаж"""
    type: str = Field(default="sales_history_update", description="Message type")
    data: Dict[str, Any] = Field(..., description="Sales data by provider")
    last_update: str = Field(..., description="Last update timestamp")
