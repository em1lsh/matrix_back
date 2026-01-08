"""Buy Orders модуль - Use Cases."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, get_uow
from app.db.models import BuyOrder, BuyOrderDealSource, BuyOrderStatus
from app.modules.buy_orders.exceptions import (
    BuyOrderNotActiveError,
    BuyOrderNotFoundError,
    BuyOrderPermissionDeniedError,
    NFTDoesNotMatchOrderError,
    NFTNotAvailableError,
    NFTNotFoundError,
    NFTNotOwnedError,
    NoMatchingNFTInStorageError,
    SelfTradeNotAllowedError,
)
from app.modules.buy_orders.repository import BuyOrderRepository
from app.modules.buy_orders.schemas import (
    BuyOrderResponse,
    BuyOrdersFilter,
    BuyOrdersListResponse,
    CreateBuyOrderRequest,
    SellToOrderRequest,
    SellToOrderResponse,
)
from app.modules.buy_orders.service import BuyOrderService
from app.utils.logger import get_logger


logger = get_logger(__name__)


class CreateBuyOrderUseCase:
    """Создание ордера на покупку."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BuyOrderRepository(session)
        self.service = BuyOrderService(self.repo)

    async def execute(self, buyer_id: int, payload: CreateBuyOrderRequest) -> BuyOrderResponse:
        price_limit = int(payload.price_ton * 1e9)
        quantity = payload.quantity or 1
        reserve = price_limit * quantity

        async with get_uow(self.session) as uow:
            buyer = await self.repo.get_user(buyer_id)
            self.service.validate_create_order(buyer, reserve)

            order = BuyOrder(
                buyer_id=buyer_id,
                title=payload.title,
                model_name=payload.model_name,
                pattern_name=payload.pattern_name,
                backdrop_name=payload.backdrop_name,
                price_limit=price_limit,
                quantity_total=quantity,
                quantity_remaining=quantity,
                frozen_amount=reserve,
                status=BuyOrderStatus.ACTIVE,
            )
            self.service.freeze_for_order(buyer, reserve)
            self.session.add(order)
            await uow.commit()
            await self.session.refresh(order)

        logger.info(
            "Buy order created",
            extra={
                "order_id": order.id,
                "buyer_id": buyer_id,
                "price_limit": price_limit,
                "quantity": quantity,
            },
        )
        return self._to_response(order)

    @staticmethod
    def _to_response(order: BuyOrder) -> BuyOrderResponse:
        return BuyOrderResponse(
            id=order.id,
            status=order.status,
            title=order.title,
            model_name=order.model_name,
            pattern_name=order.pattern_name,
            backdrop_name=order.backdrop_name,
            price_ton=order.price_limit / 1e9,
            quantity_total=order.quantity_total,
            quantity_remaining=order.quantity_remaining,
            created_at=order.created_at.isoformat() if order.created_at else "",
        )


class CancelBuyOrderUseCase:
    """Отмена ордера."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BuyOrderRepository(session)
        self.service = BuyOrderService(self.repo)

    async def execute(self, order_id: int, buyer_id: int) -> dict:
        async with get_uow(self.session) as uow:
            order = await self.repo.get_order_for_update(order_id)
            if not order:
                raise BuyOrderNotFoundError(order_id)
            if order.buyer_id != buyer_id:
                raise BuyOrderPermissionDeniedError(order_id)
            if order.status != BuyOrderStatus.ACTIVE or order.quantity_remaining <= 0:
                raise BuyOrderNotActiveError(order_id)

            buyer = order.buyer or await self.repo.get_user(buyer_id)
            refunded = self.service.unfreeze_order_remaining(buyer, order)
            await uow.commit()

        return {
            "success": True,
            "order_id": order_id,
            "refunded_ton": refunded / 1e9,
        }


class ListBuyOrdersUseCase:
    """Список ордеров."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BuyOrderRepository(session)
        self.service = BuyOrderService(self.repo)

    async def execute(self, filter: BuyOrdersFilter) -> BuyOrdersListResponse:
        self.service.validate_sort(filter.sort)
        price_min = int(filter.price_min * 1e9) if filter.price_min is not None else None
        price_max = int(filter.price_max * 1e9) if filter.price_max is not None else None

        items, total = await self.repo.list_orders(filter, price_min, price_max)
        responses = [self._to_response(order) for order in items]
        return BuyOrdersListResponse(
            items=responses,
            total=total,
            limit=filter.limit,
            offset=filter.offset,
            has_more=(filter.offset + len(items)) < total,
        )

    @staticmethod
    def _to_response(order: BuyOrder) -> BuyOrderResponse:
        return BuyOrderResponse(
            id=order.id,
            status=order.status,
            title=order.title,
            model_name=order.model_name,
            pattern_name=order.pattern_name,
            backdrop_name=order.backdrop_name,
            price_ton=order.price_limit / 1e9,
            quantity_total=order.quantity_total,
            quantity_remaining=order.quantity_remaining,
            created_at=order.created_at.isoformat() if order.created_at else "",
        )


class ListMyActiveBuyOrdersUseCase:
    """Мои активные ордера."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BuyOrderRepository(session)
        self.service = BuyOrderService(self.repo)

    async def execute(self, buyer_id: int, filter: BuyOrdersFilter) -> BuyOrdersListResponse:
        filter_data = filter.model_copy()
        filter_data.status = BuyOrderStatus.ACTIVE
        self.service.validate_sort(filter_data.sort)

        price_min = int(filter_data.price_min * 1e9) if filter_data.price_min is not None else None
        price_max = int(filter_data.price_max * 1e9) if filter_data.price_max is not None else None

        items, total = await self.repo.list_orders(filter_data, price_min, price_max, buyer_id=buyer_id)
        responses = [self._to_response(order) for order in items]
        return BuyOrdersListResponse(
            items=responses,
            total=total,
            limit=filter_data.limit,
            offset=filter_data.offset,
            has_more=(filter_data.offset + len(items)) < total,
        )

    @staticmethod
    def _to_response(order: BuyOrder) -> BuyOrderResponse:
        return BuyOrderResponse(
            id=order.id,
            status=order.status,
            title=order.title,
            model_name=order.model_name,
            pattern_name=order.pattern_name,
            backdrop_name=order.backdrop_name,
            price_ton=order.price_limit / 1e9,
            quantity_total=order.quantity_total,
            quantity_remaining=order.quantity_remaining,
            created_at=order.created_at.isoformat() if order.created_at else "",
        )


class SellToBuyOrderUseCase:
    """Продажа NFT в выбранный ордер (manual sell)."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BuyOrderRepository(session)
        self.service = BuyOrderService(self.repo)

    async def execute(self, order_id: int, seller_id: int, payload: SellToOrderRequest) -> SellToOrderResponse:
        order_preview = await self.repo.get_order(order_id)
        if not order_preview:
            raise BuyOrderNotFoundError(order_id)
        if order_preview.status != BuyOrderStatus.ACTIVE or order_preview.quantity_remaining <= 0:
            raise BuyOrderNotActiveError(order_id)
        if order_preview.buyer_id == seller_id:
            raise SelfTradeNotAllowedError()

        nft_candidate_id = payload.nft_id
        if nft_candidate_id is None:
            nft_preview = await self.repo.find_matching_nft_for_order(order_preview, seller_id, for_update=False)
            if not nft_preview:
                raise NoMatchingNFTInStorageError(order_id)
            nft_candidate_id = nft_preview.id

        from app.utils.locks import redis_lock

        async with redis_lock(f"nft:buy:{nft_candidate_id}", timeout=10), get_uow(self.session) as uow:
            order = await self.repo.get_active_order_for_update(order_id)
            if not order or order.status != BuyOrderStatus.ACTIVE or order.quantity_remaining <= 0:
                raise BuyOrderNotActiveError(order_id)
            if order.buyer_id == seller_id:
                raise SelfTradeNotAllowedError()

            nft = await self.repo.get_nft_with_gift_and_user(nft_candidate_id, for_update=True)
            if not nft:
                raise NFTNotFoundError(nft_candidate_id)

            if nft.user_id != seller_id:
                raise NFTNotOwnedError(nft.id)
            if nft.account_id is not None:
                raise NFTNotAvailableError(nft.id)

            if nft.gift.title != order.title:
                raise NFTDoesNotMatchOrderError(order.id, nft.id)
            if order.model_name and nft.gift.model_name != order.model_name:
                raise NFTDoesNotMatchOrderError(order.id, nft.id)
            if order.pattern_name and nft.gift.pattern_name != order.pattern_name:
                raise NFTDoesNotMatchOrderError(order.id, nft.id)
            if order.backdrop_name and nft.gift.backdrop_name != order.backdrop_name:
                raise NFTDoesNotMatchOrderError(order.id, nft.id)

            deal = await self.service.execute_order_fill(
                order=order,
                nft=nft,
                buyer=order.buyer,
                seller=nft.user,
                execution_price=order.price_limit,
                source=BuyOrderDealSource.MANUAL_SELL,
            )
            await uow.commit()

        return SellToOrderResponse(
            success=True,
            order_id=order_id,
            nft_id=nft_candidate_id,
            deal_id=int(deal.nft_deal_id or 0),
            price_ton=order.price_limit / 1e9,
            commission_ton=deal.commission / 1e9,
            seller_amount_ton=deal.seller_amount / 1e9,
        )


class AutoMatchBuyOrderUseCase:
    """Автоматический матчинг NFT с лучшим ордером."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BuyOrderRepository(session)
        self.service = BuyOrderService(self.repo)

    @classmethod
    async def run_for_nft_id(cls, nft_id: int) -> None:
        async with SessionLocal() as session:
            use_case = cls(session)
            try:
                await use_case.execute(nft_id)
            except Exception as exc:
                logger.opt(exception=exc).error("Auto-match failed for nft {}", nft_id)

    async def execute(self, nft_id: int) -> bool:
        from app.utils.locks import redis_lock

        async with redis_lock(f"nft:buy:{nft_id}", timeout=10), get_uow(self.session) as uow:
            nft = await self.repo.lock_nft_for_sale(nft_id)
            if not nft or nft.price is None or nft.account_id is not None:
                return False

            order = await self.repo.find_best_order_for_nft(nft)
            if not order:
                logger.info("No suitable buy order for nft {}", nft_id)
                return False

            deal = await self.service.execute_order_fill(
                order=order,
                nft=nft,
                buyer=order.buyer,
                seller=nft.user,
                execution_price=nft.price,
                source=BuyOrderDealSource.AUTO_MATCH,
            )
            await uow.commit()

        logger.info(
            "Auto-match completed",
            extra={
                "nft_id": nft_id,
                "order_id": order.id,
                "deal_id": deal.nft_deal_id,
                "execution_price": deal.execution_price,
            },
        )
        return True