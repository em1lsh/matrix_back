"""Unified модуль - Router"""

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.db import AsyncSession, get_db, models
from app.utils.cache import build_cache_key, cache_response
from app.utils.logger import get_logger

from .schemas import UnifiedFilter, UnifiedResponse
from .use_cases import GetUnifiedFeedUseCase

logger = get_logger(__name__)
router = APIRouter(prefix="/unified", tags=["Unified"])


@router.post("/", response_model=UnifiedResponse)
async def get_unified_feed(
    filter: UnifiedFilter,
    db_session: AsyncSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """
    Объединённый список подарков со всех маркетов.

    Маркеты:
    - internal: Внутренний маркет Matrix Gifts
    - mrkt: @mrkt
    - portals: @portals
    - tonnel: @tonnel

    Фильтр markets: список маркетов для запроса.
    Если пустой - запрашиваются все 4 маркета.

    Пример: {"markets": ["internal", "mrkt"]} - только внутренний и mrkt.

    Кэш 60 секунд.
    """
    cache_key = build_cache_key("unified:feed", filter)

    async def fetch_data():
        use_case = GetUnifiedFeedUseCase(db_session)
        return await use_case.execute(filter)

    return await cache_response(
        cache_key=cache_key,
        response_model=UnifiedResponse,
        fetch_func=fetch_data,
        expire=60,
    )
