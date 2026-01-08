"""Users модуль - Router"""

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user, get_user_by_init_data
from app.db import AsyncSession, get_db
from app.db.models import User
from app.utils.logger import get_logger

from .schemas import AuthTokenResponse, NFTDealsList, TransactionsList, UserResponse
from .use_cases import (
    GetAuthTokenUseCase,
    GetTransactionsUseCase,
    GetUserBuysUseCase,
    GetUserProfileUseCase,
    GetUserSellsUseCase,
)


logger = get_logger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/auth", response_model=AuthTokenResponse)
async def get_auth_token(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_user_by_init_data),
):
    """
    Получить токен авторизации

    Возвращает JWT токен текущего пользователя
    для использования в API запросах.
    """
    use_case = GetAuthTokenUseCase(session)
    return await use_case.execute(user.id)


@router.get("/me", response_model=UserResponse)
async def get_profile(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить профиль пользователя

    Возвращает полную информацию о профиле:
    - ID и язык
    - Статусы оплаты и подписки
    - Баланс на маркете (в TON)
    - Даты регистрации и платежей
    - Группу пользователя
    """
    use_case = GetUserProfileUseCase(session)
    return await use_case.execute(user.id)


@router.get("/transactions", response_model=TransactionsList)
async def get_transactions(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить историю всех транзакций

    Возвращает объединённый список пополнений и выводов,
    отсортированный по дате (новые первыми).

    Каждая транзакция содержит:
    - type: "topup" или "withdraw"
    - amount: сумма в TON
    - created_at: дата транзакции

    Параметры:
    - limit: количество элементов (по умолчанию 20)
    - offset: смещение от начала списка (по умолчанию 0)
    """
    use_case = GetTransactionsUseCase(session)
    return await use_case.execute(user.id, limit, offset)


@router.get("/sells", response_model=NFTDealsList)
async def get_sells(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить историю продаж

    Возвращает пагинированный список NFT, проданных пользователем,
    с информацией о подарке, цене и дате сделки.

    Параметры:
    - limit: количество элементов (по умолчанию 20)
    - offset: смещение от начала списка (по умолчанию 0)

    Сортировка: новые сделки первыми.
    """
    use_case = GetUserSellsUseCase(session)
    return await use_case.execute(user.id, limit, offset)


@router.get("/buys", response_model=NFTDealsList)
async def get_buys(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получить историю покупок

    Возвращает пагинированный список NFT, купленных пользователем,
    с информацией о подарке, цене и дате сделки.

    Параметры:
    - limit: количество элементов (по умолчанию 20)
    - offset: смещение от начала списка (по умолчанию 0)

    Сортировка: новые сделки первыми.
    """
    use_case = GetUserBuysUseCase(session)
    return await use_case.execute(user.id, limit, offset)
