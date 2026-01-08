"""Channels модуль - Use Cases"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_uow
from app.db.models import Channel
from app.utils.logger import get_logger

from .repository import ChannelDealRepository, ChannelRepository
from .schemas import *
from .service import ChannelService


logger = get_logger(__name__)


class GetSaleChannelsUseCase:
    def __init__(self, session: AsyncSession):
        self.repo = ChannelRepository(session)

    async def execute(self):
        channels = await self.repo.get_sale_channels()
        for ch in channels:
            if ch.price:
                ch.price = ch.price / 1e9
        return [ChannelResponse.model_validate(c) for c in channels]


class AddChannelUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ChannelRepository(session)

    async def execute(self, request: ChannelCreateRequest, user_id: int):
        async with get_uow(self.session) as uow:
            channel = Channel(username=request.channel_username, price=int(request.price_ton * 1e9), user_id=user_id)
            self.session.add(channel)
            await uow.commit()
            return {"success": True, "channel_id": channel.id}


class SetChannelPriceUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ChannelRepository(session)
        self.service = ChannelService(self.repo)

    async def execute(self, channel_id: int, price: float | None, user_id: int):
        from .exceptions import ChannelNotFoundError

        async with get_uow(self.session) as uow:
            channel = await self.repo.get_by_id(channel_id)
            if not channel:
                raise ChannelNotFoundError(channel_id)
            self.service.validate_ownership(channel, user_id)
            channel.price = int(price * 1e9) if price else None
            await uow.commit()
            return {"success": True}


class GetChannelBuysUseCase:
    def __init__(self, session: AsyncSession):
        self.repo = ChannelDealRepository(session)

    async def execute(self, user_id: int, limit: int = 20, offset: int = 0):
        """Получить историю покупок каналов"""
        deals, total = await self.repo.get_user_buys(user_id, limit, offset)

        # Конвертировать цену из nanotons в TON
        for deal in deals:
            if deal.price:
                deal.price = deal.price / 1e9

        return {
            "deals": [ChannelDealResponse.model_validate(d) for d in deals],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(deals)) < total,
        }


class GetChannelSellsUseCase:
    def __init__(self, session: AsyncSession):
        self.repo = ChannelDealRepository(session)

    async def execute(self, user_id: int, limit: int = 20, offset: int = 0):
        """Получить историю продаж каналов"""
        deals, total = await self.repo.get_user_sells(user_id, limit, offset)

        # Конвертировать цену из nanotons в TON
        for deal in deals:
            if deal.price:
                deal.price = deal.price / 1e9

        return {
            "deals": [ChannelDealResponse.model_validate(d) for d in deals],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(deals)) < total,
        }


class GetMyChannelsUseCase:
    def __init__(self, session: AsyncSession):
        self.repo = ChannelRepository(session)

    async def execute(self, user_id: int):
        """Получить свои каналы (кроме проданных)"""
        channels = await self.repo.get_user_channels(user_id)

        # Конвертировать цену из nanotons в TON
        for ch in channels:
            if ch.price:
                ch.price = ch.price / 1e9

        return [ChannelResponse.model_validate(c) for c in channels]


class DeleteChannelUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ChannelRepository(session)
        self.service = ChannelService(self.repo)

    async def execute(self, channel_id: int, user_id: int):
        """Удалить канал из базы"""
        from app.db import get_uow

        from .exceptions import ChannelNotFoundError

        async with get_uow(self.session) as uow:
            channel = await self.repo.get_by_id(channel_id)

            if not channel:
                raise ChannelNotFoundError(channel_id)

            # Проверить владение
            self.service.validate_ownership(channel, user_id)

            # Удалить канал
            await self.session.delete(channel)
            await uow.commit()

            return {"deleted": True}


class BuyChannelUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ChannelRepository(session)

    async def execute(self, receiver: str, channel_id: int, user_id: int):
        """
        Купить канал

        Сложная бизнес-логика:
        1. Проверка баланса
        2. Интеграция с Telegram API
        3. Проверка gifts_hash
        4. Передача владения каналом
        5. Расчет комиссии
        6. Создание ChannelDeal
        7. Удаление Channel
        """
        from sqlalchemy import select
        from telethon.errors.rpcerrorlist import UserNotMutualContactError

        from app.account import Account
        from app.configs import settings
        from app.db import get_uow
        from app.db.models import ChannelDeal, User

        from .exceptions import (
            ChannelGiftsModifiedError,
            ChannelNotFoundError,
            ChannelTransferError,
            InsufficientBalanceError,
            ReceiverNotSubscribedError,
        )

        async with get_uow(self.session) as uow:
            # 1. Получить канал со всеми связями
            channel = await self.repo.get_channel_for_purchase(channel_id)

            if not channel:
                raise ChannelNotFoundError(channel_id)

            # 2. Получить пользователя
            user_result = await self.session.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one()

            # 3. Проверить баланс
            if channel.price > user.market_balance:
                raise InsufficientBalanceError(channel.price, user.market_balance)

            # 4. Проверить что есть аккаунт продавца
            if not channel.account:
                raise ChannelNotFoundError(channel_id)

            # 5. Создать Account wrapper для работы с Telegram API
            acc_seller = Account(model=channel.account)

            # 6. Инициализировать Telegram клиент
            tg_cli = await acc_seller.init_telegram_client_notification(self.session)

            # 7. Получить канал через Telegram API
            tg_channel = await acc_seller.get_channel(channel_id=channel.id, telegram_client=tg_cli)

            # 8. Получить подарки канала
            channel_gifts = await acc_seller.get_channel_gifts(channel=tg_channel, telegram_client=tg_cli)

            # 9. Рассчитать gifts_hash
            gifts_hash = await acc_seller.get_gifts_hash(channel_gifts)

            # 10. Проверить что подарки не изменились
            if gifts_hash != channel.gifts_hash:
                # Удалить канал из базы
                await self.session.delete(channel)
                await uow.commit()

                # TODO: Уведомить продавца через бот
                # await change_gifts(
                #     user_id=channel.user_id,
                #     channel_name=channel.title,
                #     lang_code=user.language
                # )

                raise ChannelGiftsModifiedError(channel_id)

            # 11. Передать владение каналом через Telegram API
            try:
                buy_res = await acc_seller.channel_change_ownership(
                    reciver=receiver, channel_id=channel_id, telegram_client=tg_cli
                )
            except UserNotMutualContactError:
                raise ReceiverNotSubscribedError(receiver)

            if not buy_res:
                raise ChannelTransferError(channel_id, "Unexpected channel transmission error")

            # 12. Списать деньги с покупателя
            user.market_balance -= channel.price

            # 13. Начислить продавцу (с учетом комиссии)
            amount = channel.price - (channel.price / 100 * settings.market_comission)
            channel.user.market_balance += amount

            # 14. Создать ChannelDeal для истории
            new_deal = ChannelDeal(
                title=channel.title,
                username=channel.username,
                deal_gifts=channel.channel_gifts,
                price=channel.price,
                buyer_id=user.id,
                seller_id=channel.user_id,
            )
            self.session.add(new_deal)

            # 15. Удалить канал из базы
            await self.session.delete(channel)

            # 16. Коммит транзакции
            await uow.commit()

            # TODO: Уведомления через бот
            # await sell_channel(
            #     user_id=channel.user_id,
            #     channel_name=channel.title,
            #     amount=amount / 1e9,
            #     lang_code=channel.user.language
            # )
            # await log_buy_channel(
            #     user_id=user.id,
            #     channel_id=channel.id,
            #     channel_username=channel.username,
            #     price=channel.price / 1e9
            # )

            return {
                "success": True,
                "channel_id": channel_id,
                "price": channel.price / 1e9,
                "commission": (channel.price - amount) / 1e9,
            }
