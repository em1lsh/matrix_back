"""Unified модуль - объединённый feed со всех маркетов"""

from .router import router
from .schemas import UnifiedFilter, UnifiedResponse, SalingItem, GiftResponse, MarketInfo
from .use_cases import GetUnifiedFeedUseCase
from .repository import UnifiedRepository
from .service import UnifiedService
from .exceptions import UnifiedFeedError, MarketFetchError, InvalidMarketError

__all__ = [
    "router",
    "UnifiedFilter",
    "UnifiedResponse",
    "SalingItem",
    "GiftResponse",
    "MarketInfo",
    "GetUnifiedFeedUseCase",
    "UnifiedRepository",
    "UnifiedService",
    "UnifiedFeedError",
    "MarketFetchError",
    "InvalidMarketError",
]
