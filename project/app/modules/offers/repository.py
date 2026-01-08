from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models import NFT, NFTOffer, NFTOrderEventLog, User
from app.shared.base_repository import BaseRepository

from .exceptions import OfferNotFoundError


class OfferRepository(BaseRepository[NFTOffer]):
    """Репозиторий офферов"""

    def __init__(self, session: AsyncSession):
        super().__init__(NFTOffer, session)

    async def get_user_offers(self, user_id: int, limit: int, offset: int) -> tuple[list[NFTOffer], int]:
        """Получить офферы пользователя с пагинацией (единый список)"""
        from sqlalchemy import func, or_

        count_query = (
            select(func.count())
            .select_from(NFTOffer)
            .join(NFT, NFTOffer.nft_id == NFT.id)
            .where(or_(NFTOffer.user_id == user_id, NFT.user_id == user_id))
        )
        total = await self.session.scalar(count_query) or 0

        offers = await self.session.execute(
            select(NFTOffer)
            .join(NFT, NFTOffer.nft_id == NFT.id)
            .where(or_(NFTOffer.user_id == user_id, NFT.user_id == user_id))
            .options(
                joinedload(NFTOffer.nft).joinedload(NFT.gift),
                joinedload(NFTOffer.nft).joinedload(NFT.user),
                joinedload(NFTOffer.user),
            )
            .order_by(NFTOffer.updated.desc())
            .limit(limit)
            .offset(offset)
        )

        return (
            list(offers.unique().scalars().all()),
            total,
        )

    async def get_with_nft(self, offer_id: int) -> NFTOffer:
        """Получить оффер с NFT"""
        result = await self.session.execute(
            select(NFTOffer)
            .where(NFTOffer.id == offer_id)
            .options(
                selectinload(NFTOffer.nft).selectinload(NFT.gift),
                selectinload(NFTOffer.nft).selectinload(NFT.user),
                selectinload(NFTOffer.user),
            )
        )
        offer = result.scalar_one_or_none()
        if not offer:
            raise OfferNotFoundError(offer_id)
        return offer

    async def get_with_nft_and_user(self, offer_id: int, *, for_update: bool = False) -> NFTOffer | None:
        """Получить оффер с NFT и пользователем (без исключения если не найден)."""
        query = (
            select(NFTOffer)
            .where(NFTOffer.id == offer_id)
            .options(
                selectinload(NFTOffer.nft).selectinload(NFT.gift),
                selectinload(NFTOffer.nft).selectinload(NFT.user),
                selectinload(NFTOffer.user),
            )
        )
        if for_update:
            query = query.with_for_update()
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_offer_nft_id(self, offer_id: int) -> int | None:
        """Быстро получить nft_id по offer_id (без загрузки связей)."""
        return await self.session.scalar(select(NFTOffer.nft_id).where(NFTOffer.id == offer_id))

    async def get_nft_by_id_for_update(self, nft_id: int) -> NFT | None:
        """Получить NFT по id с блокировкой строки (FOR UPDATE)."""
        result = await self.session.execute(select(NFT).where(NFT.id == nft_id).with_for_update())
        nft = result.scalar_one_or_none()
        if nft:
            await self.session.refresh(nft, ["user"])
        return nft

    async def get_nft_for_offer(self, nft_id: int) -> NFT | None:
        """Получить NFT для создания оффера (с блокировкой)"""
        result = await self.session.execute(
            select(NFT)
            .where(NFT.id == nft_id, NFT.account_id.is_(None), NFT.active_bundle_id.is_(None))
            .with_for_update()
        )
        nft = result.scalar_one_or_none()
        if nft:
            await self.session.refresh(nft, ["user", "gift"])
        return nft

    async def check_existing_offer(self, nft_id: int, user_id: int) -> NFTOffer | None:
        """Проверить существование оффера"""
        result = await self.session.execute(
            select(NFTOffer).where(NFTOffer.nft_id == nft_id, NFTOffer.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def delete_old_offers(self) -> int:
        """
        Удалить офферы старше 1 дня и вернуть замороженные средства.

        ВАЖНО: Этот метод должен вызываться в контексте UoW для корректного
        возврата средств пользователям.
        """
        cutoff_date = datetime.now() - timedelta(days=1)

        old_offers = await self.session.execute(
            select(NFTOffer).where(NFTOffer.updated < cutoff_date).options(joinedload(NFTOffer.user))
        )
        old_offers = list(old_offers.unique().scalars().all())

        for offer in old_offers:
            if offer.user:
                offer.user.frozen_balance -= offer.price
                offer.user.market_balance += offer.price

        result = await self.session.execute(delete(NFTOffer).where(NFTOffer.updated < cutoff_date))
        return result.rowcount

    async def get_user_by_id(self, user_id: int) -> User:
        """Получить пользователя по ID"""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one()

    async def get_offers_for_nfts(self, nft_ids: list[int]) -> list[NFTOffer]:
        """Получить активные офферы для списка NFT"""
        if not nft_ids:
            return []

        result = await self.session.execute(
            select(NFTOffer)
            .where(NFTOffer.nft_id.in_(nft_ids))
            .order_by(NFTOffer.id)
            .options(selectinload(NFTOffer.user), selectinload(NFTOffer.nft))
            .with_for_update()
        )
        return list(result.scalars().all())


class OfferEventLogRepository(BaseRepository[NFTOrderEventLog]):
    """Репозиторий логов событий ордеров"""

    def __init__(self, session: AsyncSession):
        super().__init__(NFTOrderEventLog, session)

    async def create_event(
        self,
        *,
        offer_id: int | None,
        nft_id: int | None,
        actor_user_id: int | None,
        counterparty_user_id: int | None = None,
        bundle_offer_id: int | None = None,
        event_type: str,
        amount_nanotons: int | None = None,
        meta: dict | None = None,
    ) -> NFTOrderEventLog:
        event = NFTOrderEventLog(
            offer_id=offer_id,
            nft_id=nft_id,
            actor_user_id=actor_user_id,
            counterparty_user_id=counterparty_user_id,
            bundle_offer_id=bundle_offer_id,
            event_type=event_type,
            amount_nanotons=amount_nanotons,
            meta=meta,
        )
        self.session.add(event)
        await self.session.flush()
        return event