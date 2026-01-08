"""
Gift Asset модели для кеширования данных из giftasset.pro API
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base


class GiftAssetPriceList(Base):
    """Кеш цен коллекций и моделей из giftasset.pro"""
    __tablename__ = "giftasset_price_list"

    id = Column(Integer, primary_key=True, index=True)
    collection_name = Column(String(255), nullable=False, index=True)
    model_name = Column(String(255), nullable=True, index=True)
    
    # Цены по маркетплейсам
    price_getgems = Column(Float, nullable=True)
    price_mrkt = Column(Float, nullable=True)
    price_portals = Column(Float, nullable=True)
    price_tonnel = Column(Float, nullable=True)
    
    last_update = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_giftasset_price_collection_model', 'collection_name', 'model_name'),
    )


class GiftAssetVolume(Base):
    """Объемы продаж коллекций по провайдерам"""
    __tablename__ = "giftasset_volumes"

    id = Column(Integer, primary_key=True, index=True)
    collection_name = Column(String(255), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)  # mrkt, portals, tonnel
    
    # Данные за час
    hour_revenue = Column(Float, nullable=False, default=0.0)
    hour_sales = Column(Integer, nullable=False, default=0)
    
    # Данные за день
    total_revenue = Column(Float, nullable=False, default=0.0)
    total_sales = Column(Integer, nullable=False, default=0)
    
    # Пиковый час
    peak_hour = Column(DateTime, nullable=True)
    peak_hour_revenue_percent = Column(Float, nullable=False, default=0.0)
    peak_hour_sales_percent = Column(Float, nullable=False, default=0.0)
    
    sales_date = Column(Date, nullable=False, default=date.today, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_giftasset_volume_collection_provider_date', 'collection_name', 'provider', 'sales_date'),
    )


class GiftAssetEmission(Base):
    """Данные об эмиссии коллекций"""
    __tablename__ = "giftasset_emission"

    id = Column(Integer, primary_key=True, index=True)
    collection_name = Column(String(255), nullable=False, unique=True, index=True)
    
    # Основные данные эмиссии
    emission = Column(Integer, nullable=False, default=0)
    deleted = Column(Integer, nullable=False, default=0)
    hidden = Column(Integer, nullable=False, default=0)
    refunded = Column(Integer, nullable=False, default=0)
    upgraded = Column(Integer, nullable=False, default=0)
    
    # Владельцы и киты
    unique_owners = Column(Integer, nullable=False, default=0)
    top_30_whales_hold = Column(Integer, nullable=False, default=0)
    
    # Распределение по маркетплейсам
    mrkt_count = Column(Integer, nullable=False, default=0)
    portals_count = Column(Integer, nullable=False, default=0)
    tonnel_count = Column(Integer, nullable=False, default=0)
    
    # Проценты распределения
    mrkt_percentage = Column(Float, nullable=False, default=0.0)
    portals_percentage = Column(Float, nullable=False, default=0.0)
    tonnel_percentage = Column(Float, nullable=False, default=0.0)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class GiftAssetHealthIndex(Base):
    """Индекс здоровья коллекций"""
    __tablename__ = "giftasset_health_index"

    id = Column(Integer, primary_key=True, index=True)
    collection_name = Column(String(255), nullable=False, unique=True, index=True)
    
    # Основные метрики
    health_index = Column(Float, nullable=False, default=0.0)
    liquidity = Column(Integer, nullable=False, default=0)
    market_cap = Column(Float, nullable=False, default=0.0)
    whale_concentration = Column(Float, nullable=False, default=0.0)
    
    # Нормализованные метрики (0-1)
    norm_liquidity = Column(Float, nullable=False, default=0.0)
    norm_market_cap = Column(Float, nullable=False, default=0.0)
    norm_whale_concentration = Column(Float, nullable=False, default=0.0)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class GiftAssetMarketCap(Base):
    """Общая рыночная капитализация"""
    __tablename__ = "giftasset_market_cap"

    id = Column(Integer, primary_key=True, index=True)
    total_market_cap = Column(Float, nullable=False, default=0.0)
    collections_count = Column(Integer, nullable=False, default=0)
    
    # История для графиков
    record_date = Column(Date, nullable=False, default=date.today, index=True)
    record_datetime = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class GiftAssetPriceHistory(Base):
    """История цен коллекций"""
    __tablename__ = "giftasset_price_history"

    id = Column(Integer, primary_key=True, index=True)
    collection_name = Column(String(255), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)  # getgems, mrkt, portals, tonnel
    period_type = Column(String(10), nullable=False, index=True)  # 24h, 7d
    
    price = Column(Float, nullable=False)
    price_date = Column(DateTime, nullable=False, index=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_giftasset_price_history_collection_provider_date', 'collection_name', 'provider', 'price_date'),
    )


class GiftAssetProviderStats(Base):
    """Статистика провайдеров"""
    __tablename__ = "giftasset_provider_stats"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False, unique=True, index=True)
    
    # Данные за час
    hour_revenue = Column(Float, nullable=False, default=0.0)
    hour_sales = Column(Integer, nullable=False, default=0)
    
    # Данные за день
    total_revenue = Column(Float, nullable=False, default=0.0)
    total_sales = Column(Integer, nullable=False, default=0)
    
    # Пиковый час
    peak_hour = Column(String(50), nullable=True)
    peak_hour_revenue_percent = Column(Float, nullable=False, default=0.0)
    peak_hour_sales_percent = Column(Float, nullable=False, default=0.0)
    
    # Комиссия
    fee = Column(Float, nullable=False, default=0.0)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class GiftAssetSalesHistory(Base):
    """История продаж всех провайдеров"""
    __tablename__ = "giftasset_sales_history"

    id = Column(Integer, primary_key=True, index=True)
    collection_name = Column(String(255), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)
    
    price = Column(Float, nullable=False)
    telegram_gift_id = Column(String(50), nullable=False, index=True)
    telegram_gift_name = Column(String(255), nullable=False)
    telegram_gift_number = Column(Integer, nullable=False)
    
    unix_time = Column(Integer, nullable=False, index=True)
    sale_datetime = Column(DateTime, nullable=False, index=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_giftasset_sales_collection_provider_time', 'collection_name', 'provider', 'sale_datetime'),
    )


class GiftAssetMetadata(Base):
    """Метаданные коллекций и атрибутов"""
    __tablename__ = "giftasset_metadata"

    id = Column(Integer, primary_key=True, index=True)
    collection_name = Column(String(255), nullable=False, index=True)
    telegram_id = Column(String(50), nullable=True, index=True)
    
    # Метаданные в JSON формате
    backdrops = Column(JSONB, nullable=True)
    patterns = Column(JSONB, nullable=True)
    models = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class GiftAssetUpdateStat(Base):
    """Статистика обновлений данных"""
    __tablename__ = "giftasset_update_stats"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(255), nullable=False, index=True)
    last_update = Column(DateTime, nullable=False)
    update_frequency_minutes = Column(Integer, nullable=False, default=30)
    status = Column(String(50), nullable=False, default='success')  # success, error
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)