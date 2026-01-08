"""Offers модуль - Use Cases"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_uow
from app.db.models import NFT, NFTDeal, NFTOffer, User
from app.modules.nft.exceptions import NFTInBundleError
from app.utils.logger import get_logger

from .exceptions import OfferAlreadyExistsError, OfferNotFoundError
from .repository import OfferEventLogRepository, OfferRepository
from .schemas import NFTOfferResponse, NFTOffersList
from .service import OfferService


logger = get_logger(__name__)


class GetMyOffersUseCase:
    """UseCase: Получить мои офферы"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OfferRepository(session)

    async def execute(self, user_id: int, limit: int = 20, offset: int = 0) -> NFTOffersList:
        """Выполнить"""
        # Очистка старых офферов перед получением (с возвратом средств)
        await self._cleanup_old_offers()

        offers, total = await self.repo.get_user_offers(user_id, limit, offset)

        # Конвертируем цены
        for offer in offers:
            offer.price = offer.price / 1e9
            if offer.reciprocal_price:
                offer.reciprocal_price = offer.reciprocal_price / 1e9
            if offer.nft.price:
                offer.nft.price = offer.nft.price / 1e9

        offer_responses = []
        for offer in offers:
            offer_response = NFTOfferResponse.model_validate(offer).model_copy(
                update={"is_sended": offer.user_id == user_id}
            )
            offer_responses.append(offer_response)

        return NFTOffersList(
            offers=offer_responses,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(offers)) < total,
        )

    async def _cleanup_old_offers(self):
        """Очистка старых офферов с возвратом замороженных средств"""
        async with get_uow(self.session) as uow:
            deleted_count = await self.repo.delete_old_offers()
            if deleted_count > 0:
                await uow.commit()
                logger.info(f"Cleaned up {deleted_count} old offers, frozen balances returned")


class CreateOfferUseCase:
    """UseCase: Создать оффер с заморозкой средств"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OfferRepository(session)
        self.service = OfferService(self.repo)
        self.log_repo = OfferEventLogRepository(session)

    async def execute(self, nft_id: int, user_id: int, price: float):
        """
        Создать оффер с заморозкой средств.

        Бизнес-логика:
        1. Проверяем что NFT на продаже и не принадлежит пользователю
        2. Проверяем что цена оффера >= 50% от цены NFT
        3. Проверяем что у пользователя достаточно средств
        4. Замораживаем средства (market_balance -> frozen_balance)
        5. Создаём оффер
        """
        from app.utils.locks import redis_lock

        offer_price = int(price * 1e9)

        # Distributed lock для предотвращения race conditions
        async with redis_lock(f"offer:create:{nft_id}:{user_id}", timeout=10), get_uow(self.session) as uow:
            # Получаем NFT с блокировкой
            nft = await self.repo.get_nft_for_offer(nft_id)
            if not nft:
                from app.modules.nft.exceptions import NFTNotFoundError

                raise NFTNotFoundError(nft_id)

            # Проверка существующего оффера
            existing = await self.repo.check_existing_offer(nft_id, user_id)
            if existing:
                raise OfferAlreadyExistsError(nft_id, user_id)

            # Валидация возможности создания оффера
            self.service.validate_can_create_offer(nft, user_id, offer_price)

            # Получаем пользователя
            user = await self.session.get(User, user_id)

            # Проверяем и замораживаем баланс
            self.service.freeze_balance(user, offer_price)

            # Создание оффера
            offer = NFTOffer(
                nft_id=nft_id,
                user_id=user_id,
                price=offer_price,
                reciprocal_price=None,
            )
            self.session.add(offer)
            await self.session.flush()

            await self.log_repo.create_event(
                offer_id=offer.id,
                nft_id=nft_id,
                actor_user_id=user_id,
                counterparty_user_id=nft.user_id,
                event_type="created",
                amount_nanotons=offer_price,
                meta={"nft_price": nft.price},
            )
            await uow.commit()

            logger.info(
                "Offer created with frozen balance",
                extra={
                    "offer_id": offer.id,
                    "nft_id": nft_id,
                    "user_id": user_id,
                    "price_ton": price,
                    "frozen_amount": offer_price,
                },
            )

            # TODO: Отправить уведомление владельцу NFT
            # await new_offer_notif(offer, user)

            return {"created": True, "offer_id": offer.id, "frozen_amount": offer_price}


class RefuseOfferUseCase:
    """UseCase: Отклонить/отменить оффер с возвратом замороженных средств"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OfferRepository(session)
        self.service = OfferService(self.repo)
        self.log_repo = OfferEventLogRepository(session)

    async def execute(self, offer_id: int, user_id: int):
        """
        Отклонить или отменить оффер.

        Бизнес-логика:
        1. Проверяем права (владелец NFT или автор оффера)
        2. Размораживаем средства автора оффера (frozen_balance -> market_balance)
        3. Удаляем оффер
        """
        from app.utils.locks import redis_lock

        async with redis_lock(f"offer:refuse:{offer_id}", timeout=10), get_uow(self.session) as uow:
            offer = await self.repo.get_with_nft_and_user(offer_id)

            if not offer:
                raise OfferNotFoundError(offer_id)

            # Проверка прав (владелец NFT или автор оффера)
            is_nft_owner = offer.nft.user_id == user_id
            is_offer_owner = offer.user_id == user_id

            if not (is_nft_owner or is_offer_owner):
                from .exceptions import OfferPermissionDeniedError

                raise OfferPermissionDeniedError(offer_id)

            # Размораживаем средства автора оффера
            offer_author = offer.user
            self.service.unfreeze_balance(offer_author, offer.price)

            await self.log_repo.create_event(
                offer_id=offer.id,
                nft_id=offer.nft_id,
                actor_user_id=user_id,
                counterparty_user_id=offer.nft.user_id if user_id == offer.user_id else offer.user_id,
                event_type="refused",
                amount_nanotons=offer.price,
                meta={"reason": "cancelled_by_actor"},
            )

            await self.session.delete(offer)
            await uow.commit()

            logger.info(
                "Offer refused, balance unfrozen",
                extra={
                    "offer_id": offer_id,
                    "user_id": user_id,
                    "offer_author_id": offer_author.id,
                    "unfrozen_amount": offer.price,
                },
            )
            return {"deleted": True, "unfrozen_amount": offer.price}


class AcceptOfferUseCase:
    """UseCase: Принять оффер с использованием замороженных средств"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OfferRepository(session)
        self.service = OfferService(self.repo)
        self.log_repo = OfferEventLogRepository(session)

    async def execute(self, offer_id: int, user_id: int):
        """
        Принять оффер.

        Бизнес-логика:
        1. Определяем кто принимает (владелец NFT или автор оффера при встречной цене)
        2. Списываем из frozen_balance покупателя
        3. Начисляем продавцу (за вычетом комиссии)
        4. Передаём NFT
        5. Создаём запись о сделке

        Особый случай - встречная цена:
        - Если владелец NFT установил встречную цену и автор оффера её принимает,
          нужно доплатить разницу (если встречная > оффера) или вернуть (если меньше)
        """
        from app.utils.locks import redis_lock

        nft_id = await self.repo.get_offer_nft_id(offer_id)
        if nft_id is None:
            raise OfferNotFoundError(offer_id)

        async with (
            redis_lock(f"nft:state:{nft_id}", timeout=10),
            redis_lock(f"offer:accept:{offer_id}", timeout=10),
            get_uow(self.session) as uow,
        ):
            nft = await self.repo.get_nft_by_id_for_update(nft_id)
            if not nft:
                raise OfferNotFoundError(offer_id)

            offer = await self.repo.get_with_nft_and_user(offer_id, for_update=True)
            if not offer:
                raise OfferNotFoundError(offer_id)

            if offer.nft_id != nft_id:
                raise OfferNotFoundError(offer_id)

            if nft.active_bundle_id is not None:
                raise NFTInBundleError(nft.id)

            # Определяем кто принимает оффер
            is_nft_owner = nft.user_id == user_id
            is_offer_owner = offer.user_id == user_id

            buyer = offer.user
            seller = nft.user

            # Определяем цену и обрабатываем разницу
            if is_nft_owner:
                # Владелец NFT принимает оффер - используем основную цену
                # Средства уже заморожены у покупателя
                total_price = offer.price
            elif is_offer_owner and offer.reciprocal_price is not None:
                # Автор оффера принимает встречную цену
                total_price = offer.reciprocal_price
                original_frozen = offer.price

                if total_price > original_frozen:
                    # Нужно доплатить разницу
                    diff = total_price - original_frozen
                    self.service.validate_balance(buyer, diff)
                    # Замораживаем дополнительную сумму
                    self.service.freeze_balance(buyer, diff)
                elif total_price < original_frozen:
                    # Возвращаем разницу
                    diff = original_frozen - total_price
                    self.service.unfreeze_balance(buyer, diff)
                # Если равны - ничего не делаем
            else:
                from .exceptions import OfferPermissionDeniedError

                raise OfferPermissionDeniedError(offer_id)

            # Завершаем платёж из замороженных средств
            commission = self.service.complete_frozen_payment(buyer, seller, total_price)

            # Передача NFT
            old_owner_id = nft.user_id
            nft.user_id = buyer.id
            nft.price = None

            # Создать сделку
            deal = NFTDeal(
                gift_id=nft.gift_id,
                seller_id=old_owner_id,
                buyer_id=buyer.id,
                price=total_price,
            )
            self.session.add(deal)
            await self.session.flush()

            # Удалить оффер
            await self.session.delete(offer)

            await self.log_repo.create_event(
                offer_id=offer_id,
                nft_id=offer.nft_id,
                actor_user_id=user_id,
                counterparty_user_id=buyer.id if is_nft_owner else seller.id,
                event_type="accepted",
                amount_nanotons=total_price,
                meta={"commission": commission, "deal_id": deal.id},
            )

            await uow.commit()

            logger.info(
                "Offer accepted, frozen payment completed",
                extra={
                    "offer_id": offer_id,
                    "deal_id": deal.id,
                    "buyer_id": buyer.id,
                    "seller_id": old_owner_id,
                    "price": total_price,
                    "commission": commission,
                },
            )

            # TODO: Отправить уведомление о продаже
            # await sell_nft(...)

            return {"buyed": True, "deal_id": deal.id, "price": total_price, "commission": commission}


class SetReciprocalPriceUseCase:
    """UseCase: Установить встречную цену"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OfferRepository(session)
        self.service = OfferService(self.repo)
        self.log_repo = OfferEventLogRepository(session)

    async def execute(self, offer_id: int, user_id: int, price_ton: float):
        """Установить встречную цену на оффер"""
        async with get_uow(self.session) as uow:
            offer = await self.repo.get_with_nft(offer_id)

            if offer.nft.active_bundle_id is not None:
                raise NFTInBundleError(offer.nft_id)

            # Проверка что пользователь - владелец NFT
            self.service.validate_nft_owner(offer, user_id)

            # Установка встречной цены
            offer.reciprocal_price = int(price_ton * 1e9)
            offer.updated = datetime.now()

            await self.log_repo.create_event(
                offer_id=offer_id,
                nft_id=offer.nft_id,
                actor_user_id=user_id,
                counterparty_user_id=offer.user_id,
                event_type="reciprocal_set",
                amount_nanotons=offer.reciprocal_price,
                meta={"previous_price": offer.price},
            )

            await uow.commit()

            logger.info(
                "Reciprocal price set",
                extra={
                    "offer_id": offer_id,
                    "user_id": user_id,
                    "reciprocal_price_ton": price_ton,
                },
            )

            # TODO: Отправить уведомление автору оффера
            # await new_offer_notif(offer, offer.user)

            return {"updated": True}
