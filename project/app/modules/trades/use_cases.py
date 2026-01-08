"""Trades модуль - Use Cases"""

import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.configs import settings
from app.db import get_uow
from app.db.models import NFT, MarketFloor, Trade, TradeDeal, TradeProposal, TradeRequirement, User
from app.utils.logger import get_logger

from .exceptions import *
from .repository import TradeDealRepository, TradeProposalRepository, TradeRepository
from .schemas import *
from .service import TradeService


logger = get_logger(__name__)


class SearchTradesUseCase:
    def __init__(self, session: AsyncSession):
        self.repo = TradeRepository(session)

    async def execute(self, filter):
        trades = await self.repo.search(filter)
        return [TradeResponse.model_validate(t) for t in trades]


class GetMyTradesUseCase:
    def __init__(self, session: AsyncSession):
        self.repo = TradeRepository(session)

    async def execute(self, user_id: int, limit: int = 20, offset: int = 0):
        """Получить мои трейды с пагинацией"""
        trades, total = await self.repo.get_user_trades(user_id, limit, offset)

        return {
            "trades": [MyTradeResponse.model_validate(t) for t in trades],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(trades)) < total,
        }


class GetPersonalTradeUseCase:
    def __init__(self, session: AsyncSession):
        self.repo = TradeRepository(session)

    async def execute(self, user_id: int):
        """Получить персональные трейды (адресованные пользователю)"""
        trades = await self.repo.get_personal_trades(user_id)
        return [TradeResponse.model_validate(t) for t in trades]


class CreateTradeUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TradeRepository(session)

    async def execute(self, request: TradeRequest, user_id: int):
        async with get_uow(self.session) as uow:
            # Проверить что все NFT существуют и принадлежат пользователю
            nfts_result = await self.session.execute(
                select(NFT).where(NFT.id.in_(request.nft_ids), NFT.user_id == user_id)
            )
            nfts = list(nfts_result.scalars().all())

            if len(nfts) != len(request.nft_ids):
                raise NFTsNotOwnedError(request.nft_ids)

            # Создать трейд
            trade = Trade(user_id=user_id, reciver_id=request.receiver_id, nfts=nfts)
            self.session.add(trade)
            await self.session.flush()

            # Создать requirements
            for req in request.requirements:
                requirement = TradeRequirement(collection=req.collection, backdrop=req.backdrop, trade_id=trade.id)
                self.session.add(requirement)

            await uow.commit()

            # Загрузить созданный трейд с отношениями
            trade = await self.repo.get_by_id(trade.id)
            return TradeResponse.model_validate(trade)


class DeleteTradesUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TradeRepository(session)
        self.service = TradeService(self.repo)

    async def execute(self, trade_ids: list[int], user_id: int):
        async with get_uow(self.session) as uow:
            # Проверить владение или получателя
            for trade_id in trade_ids:
                trade = await self.repo.get_by_id(trade_id)
                if not trade:
                    raise TradeNotFoundError(trade_id)
                # Может удалить владелец или получатель
                if trade.user_id != user_id and trade.reciver_id != user_id:
                    raise TradePermissionDeniedError(trade_id)

            await self.repo.delete_by_ids(trade_ids)
            await uow.commit()
            return {"deleted": True}


# ============= TRADE PROPOSALS =============


class CreateProposalUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(self, request: TradeProposalRequest, user_id: int):
        """Создать предложение на трейд"""
        async with get_uow(self.session) as uow:
            # 1. Проверить что все NFT существуют и принадлежат пользователю
            nfts_result = await self.session.execute(
                select(NFT).where(NFT.id.in_(request.nft_ids), NFT.user_id == user_id).options(joinedload(NFT.gift))
            )
            nfts = list(nfts_result.scalars().all())

            if len(nfts) != len(request.nft_ids):
                raise NFTsNotOwnedError(request.nft_ids)

            # 2. Получить трейд с проверками
            trade_result = await self.session.execute(
                select(Trade)
                .where(
                    or_(Trade.reciver_id == user_id, Trade.reciver_id.is_(None)),
                    Trade.user_id != user_id,
                    Trade.id == request.trade_id,
                )
                .options(joinedload(Trade.proposals), joinedload(Trade.requirements))
            )
            trade = trade_result.unique().scalar_one_or_none()

            if not trade:
                raise TradeNotFoundError(request.trade_id)

            # 3. Проверить что пользователь еще не создавал proposal
            for old_proposal in trade.proposals:
                if old_proposal.user_id == user_id:
                    raise ProposalAlreadyExistsError(trade.id)

            # 4. Валидировать что NFT соответствуют requirements
            backup_nfts = nfts.copy()
            accepted_requirements = []

            for requirement in trade.requirements:
                approve_requirement = False
                for nft in nfts:
                    gift = nft.gift
                    # Проверка collection
                    if requirement.collection == gift.title:
                        approve_requirement = True
                    # Проверка backdrop (если указан)
                    if requirement.backdrop is not None and requirement.backdrop != gift.backdrop_name:
                        approve_requirement = False

                    if approve_requirement:
                        nfts.remove(nft)
                        accepted_requirements.append(requirement)
                        break

            # Проверить что все requirements удовлетворены
            if len(accepted_requirements) != len(trade.requirements):
                raise TradeRequirementsNotMetError(trade.id)

            # 5. Создать proposal
            new_proposal = TradeProposal(trade_id=request.trade_id, trade=trade, user_id=user_id, nfts=backup_nfts)
            self.session.add(new_proposal)
            await self.session.flush()

            proposal_id = new_proposal.id
            await uow.commit()

            # 6. Загрузить созданный proposal с отношениями
            proposal_repo = TradeProposalRepository(self.session)
            proposal = await proposal_repo.get_by_id_with_relations(proposal_id)

            return TradeProposalResponse.model_validate(proposal)


class GetMyProposalsUseCase:
    def __init__(self, session: AsyncSession):
        self.repo = TradeProposalRepository(session)

    async def execute(self, user_id: int):
        """Получить свои предложения к трейдам"""
        proposals = await self.repo.get_user_proposals(user_id)
        return [TradeProposalResponse.model_validate(p) for p in proposals]


class GetProposalsUseCase:
    def __init__(self, session: AsyncSession):
        self.repo = TradeProposalRepository(session)

    async def execute(self, user_id: int):
        """Получить предложения на свои трейды"""
        proposals = await self.repo.get_proposals_for_user_trades(user_id)
        return [MyTradeProposalResponse.model_validate(p) for p in proposals]


class CancelProposalUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TradeProposalRepository(session)

    async def execute(self, proposal_id: int, user_id: int):
        """Отказаться от предложения (владелец трейда)"""
        async with get_uow(self.session) as uow:
            proposal = await self.repo.get_by_id_with_relations(proposal_id)

            if not proposal:
                raise ProposalNotFoundError(proposal_id)

            # Проверить что пользователь - владелец трейда
            if proposal.trade.user_id != user_id:
                raise TradePermissionDeniedError(proposal.trade.id)

            await self.session.delete(proposal)
            await uow.commit()

            return {"canceled": True}


class AcceptProposalUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(self, proposal_id: int, user_id: int):
        """Согласиться на предложение (владелец трейда)"""
        async with get_uow(self.session) as uow:
            # 1. Получить proposal с отношениями
            proposal_repo = TradeProposalRepository(self.session)
            proposal = await proposal_repo.get_by_id_with_relations(proposal_id)

            if not proposal:
                raise ProposalNotFoundError(proposal_id)

            # 2. Проверить что пользователь - владелец трейда
            if proposal.trade.user_id != user_id:
                raise TradePermissionDeniedError(proposal.trade.id)

            # 3. Получить пользователя
            user_result = await self.session.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one()

            # 4. Рассчитать комиссию на основе MarketFloor
            models_names = [nft.gift.model_name for nft in proposal.nfts]
            models_names += [nft.gift.model_name for nft in proposal.trade.nfts]

            # Получить floor prices (за последний день)
            one_day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
            models_floor_result = await self.session.execute(
                select(MarketFloor)
                .where(MarketFloor.name.in_(models_names), MarketFloor.created_at >= one_day_ago)
                .order_by(MarketFloor.created_at.desc())
            )
            models_floor = list(models_floor_result.scalars().all())

            # Рассчитать комиссию
            total_commission = 0
            for nft in proposal.nfts:
                for model_floor in models_floor:
                    if nft.gift.model_name == model_floor.name:
                        total_commission += round(model_floor.price_nanotons / 100 * settings.trade_comission)
                        break

            # 5. Проверить баланс
            if user.market_balance < total_commission:
                raise InsufficientBalanceError(total_commission, user.market_balance)

            # 6. Списать комиссию
            user.market_balance -= total_commission

            # 7. Передать NFT
            gived = []
            for nft in proposal.nfts:
                nft.user_id = proposal.trade.user_id
                nft.price = None
                gived.append(nft.gift)

            sended = []
            for nft in proposal.trade.nfts:
                nft.user_id = proposal.user_id
                nft.price = None
                sended.append(nft.gift)

            # 8. Создать TradeDeal
            new_deal = TradeDeal(
                seller_id=proposal.trade.user_id, buyer_id=proposal.user_id, sended=sended, gived=gived
            )
            self.session.add(new_deal)
            await self.session.flush()

            deal_id = new_deal.id

            # 9. Удалить trade и proposal
            await self.session.delete(proposal.trade)
            await self.session.delete(proposal)

            await uow.commit()

            # 10. Загрузить созданный deal
            deal_repo = TradeDealRepository(self.session)
            deal = await deal_repo.get_by_id(deal_id)

            return TradeDealResponse.model_validate(deal)


class DeleteProposalsUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TradeProposalRepository(session)

    async def execute(self, proposal_ids: list[int], user_id: int):
        """Удалить свои предложения"""
        async with get_uow(self.session) as uow:
            await self.repo.delete_by_ids(proposal_ids, user_id)
            await uow.commit()
            return {"deleted": True}


class GetTradeDealsUseCase:
    def __init__(self, session: AsyncSession):
        self.repo = TradeDealRepository(session)

    async def execute(self, user_id: int, limit: int = 20, offset: int = 0):
        """Получить историю сделок по трейдам"""
        buys, sells, buys_total, sells_total = await self.repo.get_user_deals(user_id, limit, offset)

        return {
            "buys": [TradeDealResponse.model_validate(d) for d in buys],
            "sells": [TradeDealResponse.model_validate(d) for d in sells],
            "total_buys": buys_total,
            "total_sells": sells_total,
            "limit": limit,
            "offset": offset,
        }
