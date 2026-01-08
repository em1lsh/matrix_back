"""Trades модуль - Repository"""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import NFT, Trade, TradeDeal, TradeProposal
from app.shared.base_repository import BaseRepository


class TradeRepository(BaseRepository[Trade]):
    def __init__(self, session: AsyncSession):
        super().__init__(Trade, session)

    async def get_by_id(self, trade_id: int) -> Trade | None:
        """Получить трейд по ID со всеми связями"""
        result = await self.session.execute(
            select(Trade)
            .where(Trade.id == trade_id)
            .options(
                joinedload(Trade.nfts).joinedload(NFT.gift),
                joinedload(Trade.requirements),
            )
        )
        return result.unique().scalar_one_or_none()

    async def search(self, filter) -> list[Trade]:
        query = select(Trade).options(
            joinedload(Trade.nfts).joinedload(NFT.gift),
            joinedload(Trade.requirements)
        )
        query = query.offset(filter.page * filter.count).limit(filter.count)
        result = await self.session.execute(query)
        return list(result.unique().scalars().all())

    async def get_user_trades(self, user_id: int, limit: int, offset: int) -> tuple[list[Trade], int]:
        """Получить трейды пользователя с пагинацией"""
        # Count
        count_query = select(func.count()).select_from(Trade).where(Trade.user_id == user_id)
        total = await self.session.scalar(count_query) or 0

        # Data
        result = await self.session.execute(
            select(Trade)
            .where(Trade.user_id == user_id)
            .options(joinedload(Trade.nfts).joinedload(NFT.gift), joinedload(Trade.requirements))
            .limit(limit)
            .offset(offset)
            .order_by(Trade.created_at.desc())
        )
        items = list(result.unique().scalars().all())

        return items, total

    async def get_personal_trades(self, user_id: int) -> list[Trade]:
        """Получить персональные трейды (где reciver_id == user_id)"""
        result = await self.session.execute(
            select(Trade)
            .where(Trade.reciver_id == user_id)
            .options(joinedload(Trade.nfts).joinedload(NFT.gift), joinedload(Trade.requirements))
            .order_by(Trade.created_at.desc())
        )
        return list(result.unique().scalars().all())

    async def get_trade_with_proposals(self, trade_id: int) -> Trade | None:
        """Получить трейд с предложениями"""
        result = await self.session.execute(
            select(Trade)
            .where(Trade.id == trade_id)
            .options(
                joinedload(Trade.proposals), joinedload(Trade.requirements), joinedload(Trade.nfts).joinedload(NFT.gift)
            )
        )
        return result.unique().scalar_one_or_none()

    async def delete_by_ids(self, trade_ids: list[int]) -> None:
        # Сначала загружаем трейды с nfts чтобы очистить связи
        result = await self.session.execute(
            select(Trade).where(Trade.id.in_(trade_ids)).options(joinedload(Trade.nfts))
        )
        trades = list(result.unique().scalars().all())
        for trade in trades:
            trade.nfts.clear()  # Очищаем связь many-to-many
        await self.session.flush()
        # Теперь удаляем
        for trade in trades:
            await self.session.delete(trade)


class TradeProposalRepository(BaseRepository[TradeProposal]):
    def __init__(self, session: AsyncSession):
        super().__init__(TradeProposal, session)

    async def get_by_id_with_relations(self, proposal_id: int) -> TradeProposal | None:
        """Получить предложение со всеми связями"""
        result = await self.session.execute(
            select(TradeProposal)
            .where(TradeProposal.id == proposal_id)
            .options(
                joinedload(TradeProposal.trade).joinedload(Trade.nfts).joinedload(NFT.gift),
                joinedload(TradeProposal.trade).joinedload(Trade.requirements),
                joinedload(TradeProposal.nfts).joinedload(NFT.gift),
            )
        )
        return result.unique().scalar_one_or_none()

    async def get_user_proposals(self, user_id: int) -> list[TradeProposal]:
        """Получить предложения пользователя"""
        result = await self.session.execute(
            select(TradeProposal)
            .where(TradeProposal.user_id == user_id)
            .options(
                joinedload(TradeProposal.trade).joinedload(Trade.nfts).joinedload(NFT.gift),
                joinedload(TradeProposal.trade).joinedload(Trade.requirements),
                joinedload(TradeProposal.nfts).joinedload(NFT.gift),
            )
            .order_by(TradeProposal.created_at.desc())
        )
        return list(result.unique().scalars().all())

    async def get_proposals_for_user_trades(self, user_id: int) -> list[TradeProposal]:
        """Получить предложения на трейды пользователя"""
        # Сначала получаем ID трейдов пользователя
        trade_ids_result = await self.session.execute(select(Trade.id).where(Trade.user_id == user_id))
        trade_ids = list(trade_ids_result.scalars().all())

        if not trade_ids:
            return []

        # Затем получаем предложения на эти трейды
        result = await self.session.execute(
            select(TradeProposal)
            .where(TradeProposal.trade_id.in_(trade_ids))
            .options(
                joinedload(TradeProposal.trade).joinedload(Trade.nfts).joinedload(NFT.gift),
                joinedload(TradeProposal.trade).joinedload(Trade.requirements),
                joinedload(TradeProposal.nfts).joinedload(NFT.gift),
            )
            .order_by(TradeProposal.created_at.desc())
        )
        return list(result.unique().scalars().all())

    async def delete_by_ids(self, proposal_ids: list[int], user_id: int) -> None:
        """Удалить предложения пользователя"""
        await self.session.execute(
            delete(TradeProposal).where(TradeProposal.id.in_(proposal_ids), TradeProposal.user_id == user_id)
        )


class TradeDealRepository(BaseRepository[TradeDeal]):
    def __init__(self, session: AsyncSession):
        super().__init__(TradeDeal, session)

    async def get_user_deals(
        self, user_id: int, limit: int, offset: int
    ) -> tuple[list[TradeDeal], list[TradeDeal], int, int]:
        """Получить сделки пользователя (покупки и продажи) с пагинацией"""
        # Покупки
        buys_count = (
            await self.session.scalar(select(func.count()).select_from(TradeDeal).where(TradeDeal.buyer_id == user_id))
            or 0
        )

        buys_result = await self.session.execute(
            select(TradeDeal)
            .where(TradeDeal.buyer_id == user_id)
            .options(joinedload(TradeDeal.sended), joinedload(TradeDeal.gived))
            .limit(limit)
            .offset(offset)
            .order_by(TradeDeal.created_at.desc())
        )
        buys = list(buys_result.unique().scalars().all())

        # Продажи
        sells_count = (
            await self.session.scalar(select(func.count()).select_from(TradeDeal).where(TradeDeal.seller_id == user_id))
            or 0
        )

        sells_result = await self.session.execute(
            select(TradeDeal)
            .where(TradeDeal.seller_id == user_id)
            .options(joinedload(TradeDeal.sended), joinedload(TradeDeal.gived))
            .limit(limit)
            .offset(offset)
            .order_by(TradeDeal.created_at.desc())
        )
        sells = list(sells_result.unique().scalars().all())

        return buys, sells, buys_count, sells_count
