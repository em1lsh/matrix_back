"""Presale модуль - Router"""

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.db import AsyncSession, get_db
from app.db.models import User
from app.utils.logger import get_logger

from .schemas import *
from .use_cases import *


logger = get_logger(__name__)
router = APIRouter(prefix="/presales", tags=["PreSales"])


@router.post("/", response_model=list[NFTPreSale])
async def search_presales(
    filter: SalingFilter,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получение списка товаров на премаркете.

    Поддерживает фильтрацию по:
    - Коллекциям (titles)
    - Моделям (models)
    - Паттернам (patterns)
    - Фонам (backdrops)
    - Номеру (num)
    - Сортировку и пагинацию
    """
    return await SearchPresalesUseCase(session).execute(filter)


@router.get("/my")
async def get_my_presales(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить все свои пресейлы.

    Возвращает пагинированный список пресейлов пользователя независимо от статуса.

    Параметры:
    - limit: количество элементов (по умолчанию 20)
    - offset: смещение от начала списка (по умолчанию 0)
    """
    return await GetMyPresalesUseCase(session).execute(user.id, limit, offset)


@router.get("/set-price")
async def set_price(
    presale_id: int,
    price_ton: float,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Установить цену на пресейл.

    При установке цены списывается комиссия 20% от цены.
    Если цена уже была установлена, старая комиссия возвращается.

    Args:
        presale_id: ID пресейла
        price_ton: Цена в TON

    Raises:
        InsufficientBalanceError: Недостаточно средств для комиссии
        PresalePermissionDeniedError: Нет прав на пресейл
        PresaleNotFoundError: Пресейл не найден
    """
    return await SetPresalePriceUseCase(session).execute(presale_id, user.id, price_ton)


@router.get("/delete")
async def delete_presale(
    presale_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Удалить пресейл.

    Если была установлена цена, комиссия возвращается.
    Нельзя удалить уже купленный пресейл.

    Raises:
        PresaleAlreadyBoughtError: Пресейл уже куплен
        PresalePermissionDeniedError: Нет прав на пресейл
        PresaleNotFoundError: Пресейл не найден
    """
    return await DeletePresaleUseCase(session).execute(presale_id, user.id)


@router.get("/buy")
async def buy_presale(
    presale_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Купить пресейл.

    Покупатель платит полную цену.
    После покупки пресейл становится недоступен для других.

    Args:
        presale_id: ID пресейла

    Raises:
        InsufficientBalanceError: Недостаточно средств
        PresaleNotAvailableError: Пресейл недоступен
        PresaleAlreadyBoughtError: Пресейл уже куплен
        PresalePermissionDeniedError: Попытка купить свой пресейл
        PresaleNotFoundError: Пресейл не найден
    """
    return await BuyPresaleUseCase(session).execute(presale_id, user.id)
