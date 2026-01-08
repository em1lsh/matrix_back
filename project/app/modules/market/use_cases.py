"""Market модуль - Use Cases"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.functions import log_withdrawal
from app.configs import settings
from app.db import get_uow
from app.db.models import User
from app.utils.locks import redis_lock
from app.utils.logger import get_logger
from app.utils.retry import retry_async
from app.wallet import TonWallet

from .exceptions import WithdrawalFailedError
from .repository import MarketRepository
from .schemas import *
from .service import MarketService


logger = get_logger(__name__)


class SearchNFTsUseCase:
    """UseCase: Поиск NFT на маркете"""

    def __init__(self, session: AsyncSession):
        self.repo = MarketRepository(session)

    async def execute(self, filter: SalingFilter) -> list[SalingResponse]:
        """Выполнить"""
        items, total = await self.repo.search_nfts(filter)

        # Конвертируем цены
        for item in items:
            if item.price:
                item.price = item.price / 1e9

        return [SalingResponse.model_validate(item) for item in items]


class GetPatternsUseCase:
    """UseCase: Получить паттерны"""

    def __init__(self, session: AsyncSession):
        self.repo = MarketRepository(session)
        self.service = MarketService(self.repo)

    async def execute(self, collections: list[str]) -> list[PatternFilterResponse]:
        """Выполнить"""
        data = await self.repo.get_patterns(collections)
        return self.service.format_patterns(data)


class GetBackdropsUseCase:
    """UseCase: Получить фоны"""

    def __init__(self, session: AsyncSession):
        self.repo = MarketRepository(session)
        self.service = MarketService(self.repo)

    async def execute(self) -> list[BackdropFilterResponse]:
        """Выполнить"""
        data = await self.repo.get_backdrops()
        return self.service.format_backdrops(data)


class GetModelsUseCase:
    """UseCase: Получить модели"""

    def __init__(self, session: AsyncSession):
        self.repo = MarketRepository(session)
        self.service = MarketService(self.repo)

    async def execute(self, collections: list[str]) -> list[ModelFilterResponse]:
        """Выполнить"""
        data = await self.repo.get_models(collections)
        return self.service.format_models(data)


class GetCollectionsUseCase:
    """UseCase: Получить коллекции"""

    def __init__(self, session: AsyncSession):
        self.repo = MarketRepository(session)
        self.service = MarketService(self.repo)

    async def execute(self) -> list[CollectionFilterResponse]:
        """Выполнить"""
        titles = await self.repo.get_collections()
        return self.service.format_collections(titles)


class GetTopupInfoUseCase:
    """UseCase: Получить реквизиты для пополнения"""

    def __init__(self, session: AsyncSession):
        pass

    async def execute(self, ton_amount: float, user: User) -> PayResponse:
        """Выполнить"""
        return PayResponse(amount=ton_amount, wallet=settings.output_wallet, memo=user.memo)


class WithdrawBalanceUseCase:
    """UseCase: Вывод средств"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = MarketRepository(session)
        self.service = MarketService(self.repo)

    async def execute(self, request: WithdrawRequest, user: User) -> dict:
        """Выполнить вывод"""
        # Distributed lock
        async with redis_lock(f"withdraw:{user.id}", timeout=30), get_uow(self.session) as uow:
            # Проверка idempotency key
            if request.idempotency_key:
                existing = await self.repo.check_idempotency_key(request.idempotency_key)
                if existing:
                    logger.info("Duplicate withdrawal request", extra={"idempotency_key": request.idempotency_key})
                    return {"output": True, "idempotent": True, "withdraw_id": existing.id}

            # Валидация
            self.service.validate_withdrawal_balance(user, request.ton_amount)
            self.service.validate_ton_address(request.address)

            # Списание средств
            required_nanotons = int(request.ton_amount * 1e9)
            user.market_balance -= required_nanotons

            logger.info(
                "Processing withdrawal",
                extra={
                    "user_id": user.id,
                    "amount_ton": request.ton_amount,
                    "address": request.address,
                },
            )

            # Отправка TON
            wallet = TonWallet()
            ton_client = wallet.init_ton_client()

            try:
                await retry_async(
                    wallet.send_ton,
                    to_address=request.address,
                    amount=request.ton_amount - settings.ton_comission,
                    ton_client=ton_client,
                    is_nano=False,
                    max_attempts=3,
                    delay=2.0,
                )
            except Exception as e:
                logger.opt(exception=e).error(
                    "TON withdrawal failed: {error}",
                    error=e,
                    extra={"user_id": user.id, "amount": request.ton_amount},
                )
                raise WithdrawalFailedError(str(e))

            # Логирование
            await log_withdrawal(user_id=user.id, amount=request.ton_amount)

            # Создание записи
            withdraw = await self.repo.create_withdraw(
                user_id=user.id, amount=request.ton_amount, idempotency_key=request.idempotency_key
            )

            # Commit
            await uow.commit()

            logger.info(
                "Withdrawal completed",
                extra={"user_id": user.id, "withdraw_id": withdraw.id, "new_balance": user.market_balance},
            )

            return {"output": True, "idempotent": False, "withdraw_id": withdraw.id}


class GetIntegrationsUseCase:
    """UseCase: Получить интеграции"""

    def __init__(self, session: AsyncSession):
        self.repo = MarketRepository(session)

    async def execute(self) -> list[MarketResponse]:
        """Выполнить"""
        markets = await self.repo.get_integrations()
        return [MarketResponse.model_validate(m) for m in markets]


class GetChartUseCase:
    """UseCase: Получить график цен"""

    def __init__(self, session: AsyncSession):
        self.repo = MarketRepository(session)
        self.service = MarketService(self.repo)

    async def execute(self, filter: MarketFloorFilter) -> MarketChartResponse:
        """Выполнить"""
        floors = await self.repo.get_floor_history(filter)
        actual_floors = self.service.filter_floor_history(floors)

        return MarketChartResponse(name=filter.name, floors=actual_floors)


class GetFloorUseCase:
    """UseCase: Получить минимальную цену"""

    def __init__(self, session: AsyncSession):
        self.repo = MarketRepository(session)

    async def execute(self, filter: MarketFloorFilter) -> MarketFloorResponse | None:
        """Выполнить"""
        floor = await self.repo.get_latest_floor(filter.name)

        if not floor:
            return None

        return MarketFloorResponse.model_validate(floor)
