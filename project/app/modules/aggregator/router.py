"""Aggregator модуль - Router"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import get_current_user
from app.configs import settings
from app.db import models
from app.utils.cache import build_cache_key, cache_response
from app.utils.logger import get_logger
from app.modules.unified.schemas import UnifiedResponse

from .exceptions import (
    AggregatorAPIError,
    AggregatorRateLimitError,
    AggregatorUnauthorizedError,
)
from .schemas import AggregatorFilter
from .service import AggregatorService
from .use_cases import GetAggregatorFeedUseCase

logger = get_logger(__name__)
router = APIRouter(prefix="/aggregator", tags=["Aggregator"])


@router.post("/", response_model=UnifiedResponse)
async def get_aggregator_feed(
    payload: AggregatorFilter,
    page: int = 1,
    _user: models.User = Depends(get_current_user),
) -> UnifiedResponse:
    """
    Получить агрегированные данные из внешнего API и вернуть в unified формате.

    Кэш 60 секунд.
    """
    if page < 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="page must be >= 1")

    cache_key = build_cache_key("aggregator:feed", payload, page=page)

    async def fetch_data() -> UnifiedResponse:
        service = AggregatorService(
            base_url=settings.swiftgifts_api_url,
            api_key=settings.swiftgifts_api_key,
        )
        use_case = GetAggregatorFeedUseCase(service)
        return await use_case.execute(payload, page)

    try:
        return await cache_response(
            cache_key=cache_key,
            response_model=UnifiedResponse,
            fetch_func=fetch_data,
            expire=60,
        )
    except AggregatorUnauthorizedError as exc:
        logger.warning("Aggregator unauthorized: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Aggregator API unauthorized")
    except AggregatorRateLimitError as exc:
        logger.warning("Aggregator rate limit: %s", exc)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Aggregator API rate limit")
    except AggregatorAPIError as exc:
        logger.warning("Aggregator API error: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Aggregator API error")
