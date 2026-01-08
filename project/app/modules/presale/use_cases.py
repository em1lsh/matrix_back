"""Presale модуль - Use Cases"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_uow
from app.utils.logger import get_logger

from .repository import PresaleRepository
from .schemas import NFTPreSale
from .service import PresaleService


logger = get_logger(__name__)


class SearchPresalesUseCase:
    """UseCase: Поиск пресейлов"""

    def __init__(self, session: AsyncSession):
        self.repo = PresaleRepository(session)

    async def execute(self, filter):
        """Выполнить поиск"""
        items, total = await self.repo.search(filter)
        # Конвертируем цены в TON
        for item in items:
            if item.price:
                item.price = item.price / 1e9
        return [NFTPreSale.model_validate(i) for i in items]


class GetMyPresalesUseCase:
    """UseCase: Получить мои пресейлы"""

    def __init__(self, session: AsyncSession):
        self.repo = PresaleRepository(session)

    async def execute(self, user_id: int, limit: int = 20, offset: int = 0):
        """Выполнить"""
        items, total = await self.repo.get_user_presales(user_id, limit, offset)
        # Конвертируем цены в TON
        for item in items:
            if item.price:
                item.price = item.price / 1e9

        return {
            "presales": [NFTPreSale.model_validate(i) for i in items],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(items)) < total,
        }


class SetPresalePriceUseCase:
    """UseCase: Установить цену на пресейл"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PresaleRepository(session)
        self.service = PresaleService(self.repo)

    async def execute(self, presale_id: int, user_id: int, price: float | None):
        """
        Установить цену на пресейл.
        При установке цены списывается комиссия 20% от цены.
        """
        async with get_uow(self.session) as uow:
            # Получаем пресейл с пользователем
            presale = await self.repo.get_by_id_with_relations(presale_id)
            user = presale.user

            # Валидация владельца
            self.service.validate_ownership(presale, user_id)

            # Если устанавливается цена
            if price is not None:
                price_nanotons = int(price * 1e9)

                # Проверка баланса для комиссии (20%)
                self.service.validate_balance_for_listing(user, price_nanotons)

                # Возврат старой комиссии, если цена уже была установлена
                if presale.price is not None:
                    self.service.refund_listing_commission(user, presale.price)

                # Списание новой комиссии
                commission = self.service.calculate_listing_commission(price_nanotons)
                user.market_balance -= commission

                presale.price = price_nanotons

                logger.info(
                    "Presale price set",
                    extra={
                        "presale_id": presale_id,
                        "user_id": user_id,
                        "price_ton": price,
                        "commission": commission,
                        "new_balance": user.market_balance,
                    },
                )
            else:
                # Снятие с продажи - возврат комиссии
                if presale.price is not None:
                    self.service.refund_listing_commission(user, presale.price)

                presale.price = None

                logger.info(
                    "Presale delisted",
                    extra={"presale_id": presale_id, "user_id": user_id, "new_balance": user.market_balance},
                )

            await uow.commit()
            return {"success": True}


class DeletePresaleUseCase:
    """UseCase: Удалить пресейл"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PresaleRepository(session)
        self.service = PresaleService(self.repo)

    async def execute(self, presale_id: int, user_id: int):
        """
        Удалить пресейл.
        Если была установлена цена, возвращается комиссия.
        """
        async with get_uow(self.session) as uow:
            # Получаем пресейл с пользователем
            presale = await self.repo.get_by_id_with_relations(presale_id)
            user = presale.user

            # Валидация владельца
            self.service.validate_ownership(presale, user_id)

            # Проверка что пресейл не куплен
            if presale.buyer_id is not None:
                from .exceptions import PresaleAlreadyBoughtError

                raise PresaleAlreadyBoughtError(presale_id)

            # Возврат комиссии, если цена была установлена
            if presale.price is not None:
                self.service.refund_listing_commission(user, presale.price)

            # Удаление
            await self.session.delete(presale)

            logger.info(
                "Presale deleted",
                extra={"presale_id": presale_id, "user_id": user_id, "refunded": presale.price is not None},
            )

            await uow.commit()
            return {"success": True}


class BuyPresaleUseCase:
    """UseCase: Купить пресейл"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PresaleRepository(session)
        self.service = PresaleService(self.repo)

    async def execute(self, presale_id: int, buyer_id: int):
        """
        Купить пресейл.
        Покупатель платит полную цену, продавец получает цену минус комиссия (уже списана).
        """
        async with get_uow(self.session) as uow:
            # Получаем пресейл с пользователем
            presale = await self.repo.get_by_id_with_relations(presale_id)
            buyer = await self.repo.get_user_by_id(buyer_id)

            # Валидация доступности
            self.service.validate_presale_available(presale)

            # Проверка что покупатель не владелец
            if presale.user_id == buyer_id:
                from .exceptions import PresalePermissionDeniedError

                raise PresalePermissionDeniedError(presale_id)

            # Проверка баланса покупателя
            self.service.validate_balance_for_purchase(buyer, presale.price)

            # Списание средств у покупателя
            buyer.market_balance -= presale.price

            # Установка покупателя
            presale.buyer_id = buyer_id

            logger.info(
                "Presale bought",
                extra={
                    "presale_id": presale_id,
                    "buyer_id": buyer_id,
                    "seller_id": presale.user_id,
                    "price": presale.price,
                    "buyer_new_balance": buyer.market_balance,
                },
            )

            await uow.commit()
            return {"success": True, "bought": True}
