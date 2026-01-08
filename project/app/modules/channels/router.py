"""Channels модуль - Router"""

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.db import AsyncSession, get_db
from app.db.models import User
from app.utils.logger import get_logger

from .schemas import *
from .use_cases import *


logger = get_logger(__name__)
router = APIRouter(prefix="/channels", tags=["Channels"])


@router.get("", response_model=list[ChannelResponse])
async def get_sale_channels(session: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Каналы на продаже"""
    return await GetSaleChannelsUseCase(session).execute()


@router.post("/new")
async def add_channel(
    request: ChannelCreateRequest, session: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """Добавить канал (UoW)"""
    return await AddChannelUseCase(session).execute(request, user.id)


@router.get("/set-price")
async def set_price(
    channel_id: int,
    price: float | None = None,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Установить цену (UoW)"""
    return await SetChannelPriceUseCase(session).execute(channel_id, price, user.id)


@router.get("/buys")
async def get_buys(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить историю покупок каналов

    Возвращает пагинированный список каналов, купленных пользователем.
    """
    from .use_cases import GetChannelBuysUseCase

    return await GetChannelBuysUseCase(session).execute(user.id, limit, offset)


@router.get("/sells")
async def get_sells(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить историю продаж каналов

    Возвращает пагинированный список каналов, проданных пользователем.
    """
    from .use_cases import GetChannelSellsUseCase

    return await GetChannelSellsUseCase(session).execute(user.id, limit, offset)


@router.get("/my", response_model=list[ChannelResponse])
async def get_my_channels(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить свои каналы

    Возвращает каналы пользователя, загруженные в базу (кроме проданных).
    """
    from .use_cases import GetMyChannelsUseCase

    return await GetMyChannelsUseCase(session).execute(user.id)


@router.delete("")
async def delete_channel(
    channel_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Удалить канал из базы

    Удаляет канал из базы данных. Канал должен принадлежать пользователю.
    """
    from .use_cases import DeleteChannelUseCase

    return await DeleteChannelUseCase(session).execute(channel_id, user.id)


@router.get("/buy")
async def buy_channel(
    receiver: str,
    channel_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Купить канал

    Покупка канала с передачей владения через Telegram API.

    Процесс:
    1. Проверка баланса
    2. Проверка что подарки канала не изменились
    3. Передача владения через Telegram API
    4. Списание средств с покупателя
    5. Начисление продавцу (с учетом комиссии)
    6. Создание записи в истории сделок

    Rate limit: 5 запросов в минуту

    Параметры:
    - receiver: username получателя в Telegram (без @)
    - channel_id: ID канала

    Требования:
    - Получатель должен быть подписан на канал
    - Достаточный баланс для покупки
    - Подарки канала не должны быть изменены с момента выставления на продажу
    """
    from .use_cases import BuyChannelUseCase

    return await BuyChannelUseCase(session).execute(receiver, channel_id, user.id)
