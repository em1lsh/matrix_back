"""Users модуль - Use Cases"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import get_logger

from .repository import UserRepository
from .schemas import (
    AuthTokenResponse,
    NFTDealResponse,
    NFTDealsList,
    TopupsList,
    TransactionResponse,
    TransactionsList,
    UserResponse,
    WithdrawsList,
)
from .service import UserService


logger = get_logger(__name__)


class GetAuthTokenUseCase:
    """UseCase: Получить токен авторизации"""

    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)
        self.service = UserService(self.repo)

    async def execute(self, user_id: int) -> AuthTokenResponse:
        """Выполнить"""
        user = await self.repo.get_by_id(user_id)
        self.service.validate_token(user)

        return AuthTokenResponse(token=user.token)


class GetUserProfileUseCase:
    """UseCase: Получить профиль пользователя"""

    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)
        self.service = UserService(self.repo)

    async def execute(self, user_id: int) -> UserResponse:
        """Выполнить"""
        user = await self.repo.get_by_id(user_id)
        user = self.service.convert_balance_to_ton(user)

        return UserResponse.model_validate(user)


class GetTopupsUseCase:
    """UseCase: Получить пополнения"""

    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)

    async def execute(self, user_id: int, limit: int = 20, offset: int = 0) -> TopupsList:
        """Выполнить"""
        topups, total = await self.repo.get_topups(user_id, limit, offset)

        logger.info("Fetching topups", extra={"user_id": user_id, "count": len(topups), "total": total})

        return TopupsList(
            topups=topups, total=total, limit=limit, offset=offset, has_more=(offset + len(topups)) < total
        )


class GetWithdrawsUseCase:
    """UseCase: Получить выводы"""

    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)

    async def execute(self, user_id: int, limit: int = 20, offset: int = 0) -> WithdrawsList:
        """Выполнить"""
        withdraws, total = await self.repo.get_withdraws(user_id, limit, offset)

        logger.info("Fetching withdraws", extra={"user_id": user_id, "count": len(withdraws), "total": total})

        return WithdrawsList(
            withdraws=withdraws, total=total, limit=limit, offset=offset, has_more=(offset + len(withdraws)) < total
        )


class GetTransactionsUseCase:
    """UseCase: Получить все транзакции (пополнения + выводы)"""

    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)

    async def execute(self, user_id: int, limit: int = 20, offset: int = 0) -> TransactionsList:
        """Выполнить"""
        transactions, total = await self.repo.get_transactions(user_id, limit, offset)

        logger.info("Fetching transactions", extra={"user_id": user_id, "count": len(transactions), "total": total})

        return TransactionsList(
            transactions=[TransactionResponse(**t) for t in transactions],
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(transactions)) < total,
        )


class GetUserSellsUseCase:
    """UseCase: Получить продажи пользователя"""

    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)

    async def execute(self, user_id: int, limit: int = 20, offset: int = 0) -> NFTDealsList:
        """Выполнить"""
        deals, total = await self.repo.get_user_sells(user_id, limit, offset)

        # Конвертируем цены из nanotons в TON
        for deal in deals:
            deal.price = deal.price / 1e9

        logger.info("Fetching user sells", extra={"user_id": user_id, "count": len(deals), "total": total})

        return NFTDealsList(
            deals=[NFTDealResponse.model_validate(deal) for deal in deals],
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(deals)) < total,
        )


class GetUserBuysUseCase:
    """UseCase: Получить покупки пользователя"""

    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)

    async def execute(self, user_id: int, limit: int = 20, offset: int = 0) -> NFTDealsList:
        """Выполнить"""
        deals, total = await self.repo.get_user_buys(user_id, limit, offset)

        # Конвертируем цены из nanotons в TON
        for deal in deals:
            deal.price = deal.price / 1e9

        logger.info("Fetching user buys", extra={"user_id": user_id, "count": len(deals), "total": total})

        return NFTDealsList(
            deals=[NFTDealResponse.model_validate(deal) for deal in deals],
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(deals)) < total,
        )
