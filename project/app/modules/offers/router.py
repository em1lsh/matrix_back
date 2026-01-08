"""Offers модуль - Router"""

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.db import AsyncSession, get_db
from app.db.models import User
from app.utils.logger import get_logger

from .schemas import NFTOffersList
from .use_cases import *


logger = get_logger(__name__)
router = APIRouter(prefix="/offers", tags=["Offers"])


@router.get("/my", response_model=NFTOffersList)
async def get_my_offers(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить все свои офферы.

    Возвращает пагинированный список offers.
    Для каждого оффера:
    - is_sended: True если оффер отправлен пользователем, иначе получен

    Параметры:
    - limit: количество элементов (по умолчанию 20)
    - offset: смещение от начала списка (по умолчанию 0)

    Автоматически очищает офферы старше 1 дня.
    """
    use_case = GetMyOffersUseCase(session)
    return await use_case.execute(user.id, limit, offset)


@router.get("/new")
async def create_offer(
    nft_id: int,
    price_ton: float,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Создать новый оффер.

    Предлагает цену за NFT другого пользователя.
    Нельзя создать два оффера на один NFT от одного пользователя.

    Args:
        nft_id: ID NFT
        price_ton: Предлагаемая цена в TON

    Raises:
        OfferAlreadyExistsError: Оффер уже существует
    """
    use_case = CreateOfferUseCase(session)
    return await use_case.execute(nft_id, user.id, price_ton)


@router.post("/refuse")
async def refuse_offer(
    offer_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Удалить оффер.

    Может удалить:
    - Владелец NFT (отклонить предложение)
    - Автор оффера (отозвать предложение)

    Raises:
        OfferPermissionDeniedError: Нет прав на оффер
        OfferNotFoundError: Оффер не найден
    """
    use_case = RefuseOfferUseCase(session)
    return await use_case.execute(offer_id, user.id)


@router.post("/accept")
async def accept_offer(
    offer_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Принять оффер.

    Может принять:
    - Владелец NFT (принять основную цену)
    - Автор оффера (принять встречную цену, если она установлена)

    При принятии:
    - Списываются средства у покупателя
    - Начисляются средства продавцу (за вычетом комиссии маркета)
    - NFT передается покупателю
    - Создается запись о сделке

    Используется distributed lock для предотвращения race conditions.

    Raises:
        InsufficientBalanceError: Недостаточно средств
        OfferPermissionDeniedError: Нет прав на оффер
        OfferNotFoundError: Оффер не найден
    """
    use_case = AcceptOfferUseCase(session)
    return await use_case.execute(offer_id, user.id)


@router.get("/set-price")
async def set_reciprocal_price(
    offer_id: int,
    price_ton: float,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Установить встречную цену.

    Владелец NFT может предложить свою цену в ответ на оффер.
    После установки автор оффера может принять встречную цену.

    Args:
        offer_id: ID оффера
        price_ton: Встречная цена в TON

    Raises:
        OfferPermissionDeniedError: Нет прав на оффер (не владелец NFT)
        OfferNotFoundError: Оффер не найден
    """
    use_case = SetReciprocalPriceUseCase(session)
    return await use_case.execute(offer_id, user.id, price_ton)
