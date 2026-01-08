"""Auctions модуль - Router

Эндпоинты:
- POST /auctions/ - Получить активные аукционы
- GET /auctions/my - Мои аукционы
- POST /auctions/new - Создать аукцион
- GET /auctions/del - Удалить аукцион (без ставок)
- POST /auctions/cancel - Отменить аукцион (с возвратом ставок)
- POST /auctions/bid - Сделать ставку
- POST /auctions/finalize - Завершить истёкший аукцион
- POST /auctions/finalize-expired - Завершить все истёкшие (для cron)
- GET /auctions/deals - История сделок
"""

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.db import AsyncSession, get_db
from app.db.models import User
from app.utils.logger import get_logger

from .schemas import *
from .use_cases import *


logger = get_logger(__name__)
router = APIRouter(prefix="/auctions", tags=["Auctions"])


@router.post("/", response_model=AuctionListResponse)
async def get_auctions(
    filter: AuctionFilter,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получение списка активных аукционов.

    Возвращает только активные (не истекшие) аукционы с пагинацией и фильтрацией.

    Параметры фильтрации:
    - page: номер страницы (по умолчанию 0)
    - count: количество элементов на странице (по умолчанию 20)
    - sort: сортировка (price/asc, price/desc, num/asc, num/desc, model_rarity/asc, model_rarity/desc, created_at/asc, created_at/desc)
    - titles: фильтр по названиям коллекций
    - models: фильтр по моделям
    - patterns: фильтр по паттернам
    - backdrops: фильтр по фонам
    - num: точный номер NFT
    - num_min, num_max: диапазон номеров
    - price_min, price_max: диапазон цен в TON
    """
    return await GetActiveAuctionsUseCase(session).execute(filter)


@router.get("/my")
async def get_my_auctions(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить свои аукционы.

    Возвращает пагинированный список активных аукционов пользователя.

    Параметры:
    - limit: количество элементов (по умолчанию 20)
    - offset: смещение от начала списка (по умолчанию 0)
    """
    return await GetMyAuctionsUseCase(session).execute(user.id, limit, offset)


@router.post("/new")
async def create_auction(
    auction_data: NewAuctionRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Создать новый аукцион.

    NFT должен принадлежать пользователю и не быть на прямой продаже.
    Не может быть двух активных аукционов для одного NFT.

    Args:
        auction_data: Данные аукциона (nft_id, start_bid_ton, step_bid, term_hours)

    Returns:
        {"created": True, "auction_id": int}

    Raises:
        AuctionAlreadyExistsError: Аукцион для NFT уже существует
        NFTNotAvailableError: NFT на прямой продаже
        AuctionPermissionDeniedError: NFT не принадлежит пользователю
        NFTNotFoundError: NFT не найден
    """
    return await CreateAuctionUseCase(session).execute(auction_data, user.id)


@router.get("/del")
async def delete_auction(
    auction_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Удалить аукцион (только без ставок).

    Можно удалить только свой аукцион, на который ещё не было ставок.
    Если есть ставки - используйте /cancel для отмены с возвратом средств.

    Returns:
        {"deleted": True}

    Raises:
        AuctionHasBidsError: Аукцион имеет ставки (используйте /cancel)
        AuctionPermissionDeniedError: Нет прав на аукцион
        AuctionNotFoundError: Аукцион не найден
    """
    return await DeleteAuctionUseCase(session).execute(auction_id, user.id)


@router.post("/cancel")
async def cancel_auction(
    auction_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Отменить аукцион с возвратом всех ставок.

    Владелец аукциона может отменить его в любой момент.
    Все ставки будут возвращены участникам (разморожены).

    Returns:
        {
            "cancelled": True,
            "refunded_bids": int,
            "refunded_amount_ton": float
        }

    Raises:
        AuctionPermissionDeniedError: Нет прав на аукцион
        AuctionNotFoundError: Аукцион не найден
    """
    return await CancelAuctionUseCase(session).execute(auction_id, user.id)


@router.post("/bid")
async def place_bid(
    bid_data: NewBidRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Сделать ставку на аукцион.

    Правила ставок:
    - Первая ставка: >= start_bid
    - Последующие: >= last_bid + step_bid%

    При новой ставке предыдущие автоматически возвращаются участникам.
    Средства замораживаются до завершения аукциона.

    Args:
        bid_data: Данные ставки (auction_id, bid_ton)

    Returns:
        {"created": True, "bid_id": int}

    Raises:
        InsufficientBalanceError: Недостаточно средств
        BidTooLowError: Ставка слишком низкая
        AuctionExpiredError: Аукцион истёк
        CannotBidOwnAuctionError: Попытка сделать ставку на свой аукцион
        AuctionNotFoundError: Аукцион не найден
    """
    return await PlaceBidUseCase(session).execute(
        bid_data.auction_id, 
        user.id, 
        bid_data.bid_ton
    )


@router.post("/finalize")
async def finalize_auction(
    auction_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Завершить истёкший аукцион.

    Может вызвать любой пользователь для истёкшего аукциона.
    
    При наличии ставок:
    - NFT передаётся победителю (последняя ставка)
    - Продавец получает сумму за вычетом комиссии
    - Создаётся запись о сделке (AuctionDeal)

    При отсутствии ставок:
    - Аукцион просто закрывается

    Returns:
        {
            "finalized": True,
            "auction_id": int,
            "had_bids": bool,
            "deal_id": int (если были ставки),
            "price_ton": float,
            "commission_ton": float,
            "seller_amount_ton": float
        }

    Raises:
        AuctionNotExpiredError: Аукцион ещё не истёк
        AuctionNotFoundError: Аукцион не найден
    """
    return await FinalizeAuctionUseCase(session).execute(auction_id)


@router.post("/finalize-expired")
async def finalize_expired_auctions(
    limit: int = 100,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Завершить все истёкшие аукционы.

    Эндпоинт для cron/scheduler или ручного запуска.
    Обрабатывает до {limit} истёкших аукционов за раз.

    Параметры:
    - limit: максимальное количество аукционов для обработки (по умолчанию 100)

    Returns:
        {
            "processed": int,
            "results": [...]
        }
    """
    return await FinalizeExpiredAuctionsUseCase(session).execute(limit)


@router.get("/deals")
async def get_deals(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить историю сделок.

    Возвращает пагинированный список сделок пользователя (покупки и продажи).

    Параметры:
    - limit: количество элементов (по умолчанию 20)
    - offset: смещение от начала списка (по умолчанию 0)
    """
    return await GetDealsUseCase(session).execute(user.id, limit, offset)
