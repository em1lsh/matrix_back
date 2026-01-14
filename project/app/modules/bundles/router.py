from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db import get_db
from app.db.models import User

from .schemas import (
    BundleFilter,
    BundleOfferRequest,
    BundleResponse,
    BundlesListResponse,
    BuyBundleRequest,
    CancelBundleRequest,
    CreateBundleRequest,
)
from .use_cases import (
    BuyBundleUseCase,
    CancelBundleUseCase,
    CreateBundleOfferUseCase,
    CreateBundleUseCase,
    ListBundlesUseCase,
    ListUserBundlesUseCase,
)


router = APIRouter(prefix="/bundles", tags=["Bundles"])


@router.post("/list", response_model=BundlesListResponse)
async def list_bundles(
    request: BundleFilter,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список активных бандлов на маркете.

    Фильтры и сортировка:
    - titles/models/patterns/backdrops: точное совпадение характеристик подарков
    - price_min/price_max: диапазон цены в TON
    - sort: price/asc или created_at/desc
    - limit/offset: пагинация (limit до 100)
    """
    use_case = ListBundlesUseCase(session)
    return await use_case.execute(request)


@router.post("/my", response_model=BundlesListResponse)
async def list_my_bundles(
    request: BundleFilter,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список бандлов, созданных текущим пользователем.

    Структура ответа соответствует /bundles/list, но возвращаются только бандлы продавца.
    """
    use_case = ListUserBundlesUseCase(session)
    return await use_case.execute(current_user.id, request)


@router.post("/create", response_model=BundleResponse)
async def create_bundle(
    request: CreateBundleRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Создать новый бандл из своих NFT.

    ято делает:
    - dалидирует, что минимум 2 NFT, IDs уникальны и принадлежат продавцу
    - проверяет, что NFT не состоят в другом бандле
    - создает бандл с указанной ценойT
    - автоматически отменяет и очищает офферы на включенные NFT

    цена задается в TON
    """
    use_case = CreateBundleUseCase(session)
    return await use_case.execute(current_user.id, request)


@router.post("/cancel")
async def cancel_bundle(
    request: CancelBundleRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    отменить свой бандл.
    - после отмены статус меняется на cancelled, NFT освобождаются и становятся доступными отдельно
    """
    use_case = CancelBundleUseCase(session)
    return await use_case.execute(current_user.id, request.bundle_id)


@router.post("/buy")
async def buy_bundle(
    request: BuyBundleRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    купить бандл

    Процесс:
    - списывает цену с market_balance покупателя, начисляет продавцу сумму за вычетом комиссии
    - создает сделки по каждому NFT и переводит их покупателю, очищает цены и связи с бандлом
    """
    use_case = BuyBundleUseCase(session)
    return await use_case.execute(current_user.id, request)


@router.post("/offer")
async def create_bundle_offer(
    request: BundleOfferRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Сделать оффер на бандл.

    условия:
    - нельзя оставлять оффер на собственный бандл
    - только один активный оффер пользователя на конкретный бандл
    - минимальная цена — не ниже 50% от цены бандла
    - сумма оффера в TON замораживается на балансе
    """
    use_case = CreateBundleOfferUseCase(session)
    return await use_case.execute(current_user.id, request)
