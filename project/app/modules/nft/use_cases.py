"""NFT модуль - Use Cases (оркестрация)"""

import asyncio
from typing import TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.base import PaginationRequest
from app.db import get_uow
from app.utils.logger import get_logger

from .repository import NFTRepository
from .schemas import MyNFTFilter, NFTDealResponse, NFTListResponse, NFTResponse
from .service import NFTService


logger = get_logger(__name__)


class SetPriceResult(TypedDict):
    """Результат установки цены"""

    success: bool
    nft_id: int
    price_ton: float | None


class GetUserNFTsUseCase:
    """UseCase: Получить NFT пользователя"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NFTRepository(session)

    async def execute(self, user_id: int, pagination: PaginationRequest) -> NFTListResponse:
        """Выполнить"""
        items, total = await self.repo.get_user_nfts(user_id, pagination)

        # Конвертируем цены из nanotons в TON
        for item in items:
            if item.price:
                item.price = item.price / 1e9

        return NFTListResponse(
            items=[NFTResponse.model_validate(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
            has_more=(pagination.offset + len(items)) < total,
        )


class GetUserNFTsFilteredUseCase:
    """UseCase: Получить NFT пользователя с фильтрацией"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NFTRepository(session)

    async def execute(self, user_id: int, filter: MyNFTFilter) -> NFTListResponse:
        """Выполнить"""
        items, total = await self.repo.get_user_nfts_filtered(user_id, filter)

        # Конвертируем цены из nanotons в TON
        for item in items:
            if item.price:
                item.price = item.price / 1e9

        offset = filter.page * filter.count
        return NFTListResponse(
            items=[NFTResponse.model_validate(item) for item in items],
            total=total,
            limit=filter.count,
            offset=offset,
            has_more=(offset + len(items)) < total,
        )


class SetPriceUseCase:
    """UseCase: Установить цену NFT"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NFTRepository(session)
        self.service = NFTService(self.repo)

    async def execute(self, nft_id: int, user_id: int, price_ton: float | None) -> SetPriceResult:
        """Выполнить"""
        async with get_uow(self.session) as uow:
            nft = await self.service.set_price(nft_id, user_id, price_ton)
            await uow.commit()
            logger.info(
                "NFT price updated successfully", extra={"nft_id": nft_id, "user_id": user_id, "price_ton": price_ton}
            )

        if price_ton is not None:
            from app.modules.buy_orders.use_cases import AutoMatchBuyOrderUseCase

            try:
                asyncio.create_task(AutoMatchBuyOrderUseCase.run_for_nft_id(nft_id))
            except RuntimeError:
                await AutoMatchBuyOrderUseCase.run_for_nft_id(nft_id)

        return SetPriceResult(success=True, nft_id=nft.id, price_ton=price_ton)


class BuyNFTUseCase:
    """UseCase: Купить NFT"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NFTRepository(session)
        self.service = NFTService(self.repo)

    async def execute(self, nft_id: int, buyer_id: int):
        """Выполнить покупку"""
        from app.bot.functions import sell_nft
        from app.db.models import NFTDeal, User
        from app.utils.locks import redis_lock

        # Distributed lock для предотвращения двойной покупки
        async with redis_lock(f"nft:buy:{nft_id}", timeout=10), get_uow(self.session) as uow:
            # 1. Получить NFT с блокировкой
            nft = await self.repo.get_for_purchase(nft_id)
            if not nft:
                from .exceptions import NFTNotFoundError

                raise NFTNotFoundError(nft_id)

            # 2. Загрузить связи
            await self.session.refresh(nft, ["user", "gift"])

            # 3. Получить покупателя
            buyer = await self.session.get(User, buyer_id)

            # 4. Валидация баланса
            self.service.validate_balance(buyer, nft)

            # 5. Расчет комиссии
            commission, seller_amount = self.service.calculate_commission(nft.price)

            # 6. Уведомление продавца
            await sell_nft(
                gift_title=nft.gift.title,
                price=seller_amount / 1e9,
                user_id=nft.user_id,
                lang_code=nft.user.language,
            )

            # 7. Создать сделку
            deal = NFTDeal(gift_id=nft.gift_id, seller_id=nft.user_id, buyer_id=buyer.id, price=nft.price)
            self.session.add(deal)
            await self.session.flush()

            # 8. Деактивировать продвижение при продаже NFT
            from app.modules.promotion.repository import PromotionRepository
            promotion_repo = PromotionRepository(self.session)
            await promotion_repo.deactivate_promotion(nft_id)

            # 9. Финансовые операции
            buyer.market_balance -= nft.price
            nft.user.market_balance += seller_amount
            nft.user_id = buyer.id
            nft.price = None

            # 10. Commit
            await uow.commit()

            logger.info(
                "NFT purchased successfully",
                extra={
                    "nft_id": nft_id,
                    "buyer_id": buyer.id,
                    "seller_id": nft.user_id,
                    "price": nft.price,
                    "commission": commission,
                },
            )

            return {
                "success": True,
                "nft_id": nft.id,
                "deal_id": deal.id,
                "buyer_id": buyer.id,
                "seller_id": nft.user_id,
                "price": nft.price,
                "commission": commission,
            }


class GetGiftDealsUseCase:
    """UseCase: Получить сделки по подарку"""

    def __init__(self, session: AsyncSession):
        self.repo = NFTRepository(session)

    async def execute(self, gift_id: int, limit: int = 20, offset: int = 0):
        """Выполнить"""
        from .schemas import NFTDealsList

        deals, total = await self.repo.get_gift_deals(gift_id, limit, offset)

        # Конвертируем цены
        for deal in deals:
            deal.price = deal.price / 1e9

        return NFTDealsList(
            deals=[NFTDealResponse.model_validate(deal) for deal in deals],
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(deals)) < total,
        )


class BackNFTUseCase:
    """UseCase: Вернуть NFT обратно в Telegram"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NFTRepository(session)
        self.service = NFTService(self.repo)

    async def execute(self, nft_id: int, user_id: int):
        """Выполнить возврат NFT"""
        from app.account._base import Account as AccountClass
        from app.configs import settings
        from app.db.models import User

        async with get_uow(self.session) as uow:
            # 1. Получить NFT
            nft = await self.repo.get_by_id(nft_id)
            if not nft:
                from .exceptions import NFTNotFoundError

                raise NFTNotFoundError(nft_id)

            # 2. Загрузить связи
            await self.session.refresh(nft, ["user"])

            # 3. Валидация владельца
            if nft.user_id != user_id:
                from .exceptions import NFTNotOwnedError

                raise NFTNotOwnedError(nft_id)

            # 4. Проверка что NFT не привязан к аккаунту
            if nft.account_id is not None:
                from .exceptions import NFTAlreadyLinkedError

                raise NFTAlreadyLinkedError(nft_id)

            # 5. Получить пользователя
            user = await self.session.get(User, user_id)

            # 6. Проверка баланса (комиссия 0.1 TON)
            commission = int(0.1 * 1e9)
            if user.market_balance < commission:
                from .exceptions import InsufficientBalanceError

                raise InsufficientBalanceError(commission, user.market_balance)

            # 7. Получить банковский аккаунт
            bank_account = await self.repo.get_bank_account(settings.bank_account)
            if not bank_account:
                from .exceptions import BankAccountNotFoundError

                raise BankAccountNotFoundError()

            # 8. Отправить подарок через Telegram
            bank_acc = AccountClass(bank_account)
            tg_cli = await bank_acc.init_telegram_client()
            send_res = await bank_acc.send_gift(tg_cli, user.id, nft.msg_id)

            if not send_res:
                from .exceptions import GiftSendError

                raise GiftSendError(nft_id)

            # 9. Списать комиссию и удалить NFT
            user.market_balance -= commission
            await self.session.delete(nft)

            await uow.commit()

            logger.info(
                "NFT returned to Telegram successfully",
                extra={"nft_id": nft_id, "user_id": user_id, "commission": commission / 1e9},
            )

            return {"success": True, "nft_id": nft_id, "returned": send_res}
