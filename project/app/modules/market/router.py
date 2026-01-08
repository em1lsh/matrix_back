"""Market модуль - Router"""

from fastapi import APIRouter, Depends, Request
from fastapi_cache.decorator import cache

from app.api.auth import get_current_user
from app.api.cache_key_builder import request_key_builder
from app.api.limiter import limiter
from app.db import AsyncSession, get_db
from app.db.models import User
from app.utils.logger import get_logger

from .schemas import *
from .use_cases import *


logger = get_logger(__name__)
router = APIRouter(prefix="/market", tags=["Market"])


@router.post("/", response_model=list[SalingResponse])
async def search_nfts(
    filter: SalingFilter,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Поиск NFT на маркете

    Поддерживает:
    - Фильтрацию по коллекциям, моделям, паттернам, фонам
    - Фильтрацию по цене (min/max)
    - Фильтрацию по номеру NFT
    - Сортировку по различным полям
    - Пагинацию (page/count)
    """
    use_case = SearchNFTsUseCase(session)
    return await use_case.execute(filter)


@router.post("/patterns", response_model=list[PatternFilterResponse])
@cache(expire=60 * 5, key_builder=request_key_builder)
async def get_patterns(
    collections: list[str],
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Получить фильтр паттернов для коллекций"""
    use_case = GetPatternsUseCase(session)
    return await use_case.execute(collections)


@router.post("/backdrops", response_model=list[BackdropFilterResponse])
@cache(expire=60 * 5, key_builder=request_key_builder)
async def get_backdrops(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Получить фильтр фонов"""
    use_case = GetBackdropsUseCase(session)
    return await use_case.execute()


@router.post("/models", response_model=list[ModelFilterResponse])
@cache(expire=60 * 5, key_builder=request_key_builder)
async def get_models(
    collections: list[str],
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Получить фильтр моделей для коллекций"""
    use_case = GetModelsUseCase(session)
    return await use_case.execute(collections)


@router.get("/collections", response_model=list[CollectionFilterResponse])
@cache(expire=60 * 5, key_builder=request_key_builder)
async def get_collections(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Получить список всех коллекций"""
    use_case = GetCollectionsUseCase(session)
    return await use_case.execute()


@router.get("/topup-balance", response_model=PayResponse)
async def get_topup_info(
    ton_amount: float,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить реквизиты для пополнения баланса

    Возвращает адрес кошелька и memo для пополнения.
    """
    use_case = GetTopupInfoUseCase(session)
    return await use_case.execute(ton_amount, user)


@router.post("/output")
@limiter.limit("1/minute")
async def withdraw_balance(
    request: Request,
    withdraw_request: WithdrawRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Вывод средств с баланса

    Поддерживает:
    - Idempotency key для предотвращения двойных выплат
    - Distributed lock для предотвращения race conditions
    - UoW для атомарности транзакции
    - Retry механизм для отправки TON
    - Валидацию баланса и адреса

    Лимит: 1 запрос в минуту на пользователя.
    """
    use_case = WithdrawBalanceUseCase(session)
    return await use_case.execute(withdraw_request, user)


@router.get("/integrations", response_model=list[MarketResponse])
async def get_integrations(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Получить список подключенных маркетплейсов"""
    use_case = GetIntegrationsUseCase(session)
    return await use_case.execute()


@router.post("/charts", response_model=MarketChartResponse)
async def get_chart(
    filter: MarketFloorFilter,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить график изменения цены

    Возвращает историю минимальных цен для модели/коллекции
    за указанный период (1, 7 или 30 дней).
    """
    use_case = GetChartUseCase(session)
    return await use_case.execute(filter)


@router.post("/floor", response_model=MarketFloorResponse | None)
async def get_floor(
    filter: MarketFloorFilter,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить минимальную цену

    Возвращает текущую минимальную цену для модели/коллекции.
    """
    use_case = GetFloorUseCase(session)
    return await use_case.execute(filter)
