"""NFT модуль - Router (HTTP endpoints)"""

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.db import AsyncSession, get_db
from app.db.models import User
from app.utils.logger import get_logger

from .schemas import BuyRequest, MyNFTFilter, NFTDealsFilter, NFTDealsList, NFTListResponse, SetPriceRequest
from .use_cases import (
    BuyNFTUseCase,
    GetGiftDealsUseCase,
    GetUserNFTsFilteredUseCase,
    SetPriceUseCase,
)


logger = get_logger(__name__)
router = APIRouter(prefix="/nft", tags=["NFT"])


@router.post("/my", response_model=NFTListResponse)
async def get_my_nfts(
    filter: MyNFTFilter,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить список своих NFT с фильтрацией

    Возвращает пагинированный список NFT пользователя,
    которые находятся на маркете (не привязаны к аккаунту).

    Поддерживает:
    - Пагинацию (page/count)
    - Сортировку (created_at, price, num, model_rarity)
    - Фильтрацию по коллекциям, моделям, паттернам, фонам
    - Фильтрацию по номеру NFT (точный, диапазон)
    - Фильтрацию по статусу продажи (on_sale)
    """
    use_case = GetUserNFTsFilteredUseCase(session)
    return await use_case.execute(user.id, filter)


@router.post("/set-price")
async def set_price(
    request: SetPriceRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Установить цену для NFT

    Позволяет:
    - Выставить NFT на продажу с указанной ценой
    - Снять NFT с продажи (price_ton = null)

    Валидация:
    - Проверка владения NFT
    - Минимальная цена 0.1 TON
    - NFT не должен быть привязан к аккаунту

    Использует UoW для атомарности операции.
    """
    use_case = SetPriceUseCase(session)
    return await use_case.execute(request.nft_id, user.id, request.price_ton)


@router.post("/buy")
async def buy_nft(
    request: BuyRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Купить NFT

    Выполняет покупку NFT с:
    - Проверкой баланса покупателя
    - Расчетом комиссии маркета
    - Уведомлением продавца
    - Созданием записи о сделке

    Использует:
    - UoW для атомарности транзакции
    - Distributed lock для предотвращения двойной покупки
    - SELECT FOR UPDATE для блокировки NFT

    Комиссия маркета вычитается из суммы продавца.
    """
    use_case = BuyNFTUseCase(session)
    return await use_case.execute(request.nft_id, user.id)


@router.post("/deals", response_model=NFTDealsList)
async def get_deals(
    filter: NFTDealsFilter,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить сделки по подарку

    Возвращает пагинированный список сделок по указанному подарку
    для отображения истории цен и активности.

    Параметры в фильтре:
    - gift_id: ID подарка
    - limit: количество элементов (по умолчанию 20, макс 100)
    - offset: смещение от начала списка (по умолчанию 0)

    Сортировка: новые сделки первыми.
    """
    use_case = GetGiftDealsUseCase(session)
    return await use_case.execute(filter.gift_id, filter.limit, filter.offset)


@router.get("/back")
async def back_nft(
    nft_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Вернуть NFT обратно в Telegram

    Отправляет NFT обратно пользователю в Telegram через банковский аккаунт.

    Требования:
    - NFT должен принадлежать пользователю
    - NFT не должен быть привязан к аккаунту
    - Баланс пользователя >= 0.1 TON (комиссия)

    Процесс:
    1. Проверка владения и баланса
    2. Отправка подарка через Telegram API
    3. Списание комиссии 0.1 TON
    4. Удаление NFT из базы

    Использует UoW для атомарности операции.
    """
    from .use_cases import BackNFTUseCase

    use_case = BackNFTUseCase(session)
    return await use_case.execute(nft_id, user.id)
