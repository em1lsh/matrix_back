"""Trades модуль - Router"""

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.db import AsyncSession, get_db
from app.db.models import User
from app.utils.logger import get_logger

from .schemas import *
from .use_cases import *


logger = get_logger(__name__)
router = APIRouter(prefix="/trades", tags=["Trades"])


@router.post("/", response_model=list[TradeResponse])
async def search_trades(
    filter: TradeFilter, session: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """Поиск трейдов"""
    return await SearchTradesUseCase(session).execute(filter)


@router.get("/my")
async def get_my_trades(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Мои трейды

    Возвращает пагинированный список трейдов пользователя.

    Параметры:
    - limit: количество элементов (по умолчанию 20)
    - offset: смещение от начала списка (по умолчанию 0)
    """
    return await GetMyTradesUseCase(session).execute(user.id, limit, offset)


@router.post("/new", response_model=TradeResponse)
async def create_trade(
    request: TradeRequest, session: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """Создать трейд (UoW)"""
    return await CreateTradeUseCase(session).execute(request, user.id)


@router.post("/delete")
async def delete_trades(
    trade_ids: list[int], session: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """Удалить трейды (UoW)"""
    return await DeleteTradesUseCase(session).execute(trade_ids, user.id)


@router.get("/personal")
async def get_personal_trade(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить персональные трейды

    Возвращает трейды, адресованные конкретному пользователю (reciver_id).
    """
    from .use_cases import GetPersonalTradeUseCase

    return await GetPersonalTradeUseCase(session).execute(user.id)


# Trade Proposals endpoints
@router.post("/new-proposal")
async def create_proposal(
    proposal: TradeProposalRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Создать предложение на трейд"""
    from .use_cases import CreateProposalUseCase

    return await CreateProposalUseCase(session).execute(proposal, user.id)


@router.get("/my-proposals")
async def get_my_proposals(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Получить свои предложения к трейдам"""
    from .use_cases import GetMyProposalsUseCase

    return await GetMyProposalsUseCase(session).execute(user.id)


@router.get("/proposals")
async def get_proposals(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Получить предложения на свои трейды"""
    from .use_cases import GetProposalsUseCase

    return await GetProposalsUseCase(session).execute(user.id)


@router.get("/cancel-proposal")
async def cancel_proposal(
    proposal_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Отказаться от предложения (владелец трейда)"""
    from .use_cases import CancelProposalUseCase

    return await CancelProposalUseCase(session).execute(proposal_id, user.id)


@router.get("/accept-proposal")
async def accept_proposal(
    proposal_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Согласиться на предложение (владелец трейда)"""
    from .use_cases import AcceptProposalUseCase

    return await AcceptProposalUseCase(session).execute(proposal_id, user.id)


@router.post("/delete-proposals")
async def delete_proposals(
    proposal_ids: list[int],
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Удалить свои предложения"""
    from .use_cases import DeleteProposalsUseCase

    return await DeleteProposalsUseCase(session).execute(proposal_ids, user.id)


@router.get("/deals")
async def get_deals(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Получить историю сделок по трейдам"""
    from .use_cases import GetTradeDealsUseCase

    return await GetTradeDealsUseCase(session).execute(user.id, limit, offset)
