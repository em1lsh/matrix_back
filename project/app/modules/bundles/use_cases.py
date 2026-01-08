from __future__ import annotations

from contextlib import AsyncExitStack
from datetime import datetime
import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_uow
from app.db.models import NFT
from app.modules.offers.repository import OfferEventLogRepository, OfferRepository
from app.modules.offers.service import MIN_OFFER_PERCENT, OfferService
from app.modules.promotion.repository import PromotionRepository
from app.modules.nft.exceptions import NFTInBundleError
from app.modules.nft.service import NFTService
from app.utils.locks import redis_lock
from app.utils.logger import get_logger

from .exceptions import BundleNotActiveError, BundleNotFoundError, BundlePermissionDeniedError, InvalidBundleItemsError
from .repository import BundleOfferRepository, BundleRepository
from .schemas import (
    BundleFilter,
    BundleOfferRequest,
    BundleResponse,
    BundlesListResponse,
    BuyBundleRequest,
    CreateBundleRequest,
)
from .service import BundleService


logger = get_logger(__name__)


class ListBundlesUseCase:
    def __init__(self, session: AsyncSession):
        self.repo = BundleRepository(session)
        self.session = session

    async def execute(self, filter: BundleFilter) -> BundlesListResponse:
        items, total = await self.repo.list_active_bundles(filter)
        return BundleService.to_list_response(items, total, filter.limit, filter.offset)


class CreateBundleUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BundleRepository(session)
        self.promotion_repo = PromotionRepository(session)
        self.offer_repo = OfferRepository(session)
        self.offer_log_repo = OfferEventLogRepository(session)
        self.offer_service = OfferService(self.offer_repo)
        self.nft_service = NFTService(self.offer_repo)

    async def execute(self, user_id: int, request: CreateBundleRequest) -> BundleResponse:
        price_nanotons = int(request.price_ton * 1e9)
        nft_ids = request.nft_ids
        if len(nft_ids) < 2:
            raise InvalidBundleItemsError("Bundle must include at least two NFTs", nft_ids)

        nft_ids_sorted = sorted(set(nft_ids))
        sig_src = ",".join(map(str, nft_ids_sorted))
        sig = hashlib.sha256(sig_src.encode("utf-8")).hexdigest()[:16]
        lock_key = f"bundle:create:{user_id}:{sig}"

        async with AsyncExitStack() as stack:
            await stack.enter_async_context(redis_lock(lock_key, timeout=10))
            for nft_id in nft_ids_sorted:
                await stack.enter_async_context(redis_lock(f"nft:state:{nft_id}", timeout=10))

            async with get_uow(self.session) as uow:
                result = await self.session.execute(
                    select(NFT)
                    .where(NFT.id.in_(nft_ids_sorted))
                    .order_by(NFT.id)
                    .with_for_update()
                )
                nfts = list(result.scalars().all())

                if len(nfts) != len(nft_ids_sorted):
                    raise InvalidBundleItemsError("Some NFTs not found", nft_ids)

                for nft in nfts:
                    if nft.user_id != user_id:
                        raise InvalidBundleItemsError("NFT does not belong to seller", nft_ids)
                    if nft.account_id is not None:
                        raise InvalidBundleItemsError("NFT is linked to account", nft_ids)
                    if nft.active_bundle_id is not None:
                        raise NFTInBundleError(nft.id)

                bundle = await self.repo.create_bundle(user_id, price_nanotons)
                await self.repo.add_items(bundle.id, nft_ids_sorted)

                offers = await self.offer_repo.get_offers_for_nfts(nft_ids_sorted)
                for offer in offers:
                    if offer.user:
                        self.offer_service.unfreeze_balance(offer.user, offer.price)
                    await self.offer_log_repo.create_event(
                        offer_id=offer.id,
                        nft_id=offer.nft_id,
                        actor_user_id=user_id,
                        counterparty_user_id=offer.user_id,
                        event_type="auto_cancel_by_bundle",
                        amount_nanotons=offer.price,
                        meta={"bundle_id": bundle.id, "nft_id": offer.nft_id},
                    )
                    await self.session.delete(offer)

                for nft in nfts:
                    await self.promotion_repo.deactivate_promotion(nft.id)
                    nft.price = None
                    nft.active_bundle_id = bundle.id

                await uow.commit()

        logger.info(
            "Bundle created",
            extra={
                "bundle_id": bundle.id,
                "user_id": user_id,
                "nft_ids": nft_ids_sorted,
                "price_nanotons": price_nanotons,
            },
        )
        refreshed = await self.repo.get_bundle_with_items(bundle.id)
        return BundleService.to_bundle_response(refreshed or bundle)


class CancelBundleUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BundleRepository(session)
        self.bundle_offer_repo = BundleOfferRepository(session)
        self.offer_service = OfferService(self.bundle_offer_repo)
        self.offer_log_repo = OfferEventLogRepository(session)

    async def execute(self, user_id: int, bundle_id: int) -> dict:
        async with redis_lock(f"bundle:state:{bundle_id}", timeout=10), get_uow(self.session) as uow:
            bundle = await self.repo.get_bundle_for_update(bundle_id)
            if not bundle:
                raise BundleNotFoundError(bundle_id)
            if bundle.status != "active":
                raise BundleNotActiveError(bundle_id)
            if bundle.seller_id != user_id:
                raise BundlePermissionDeniedError(bundle_id)


            bundle_offers = await self.bundle_offer_repo.list_offers_for_bundle_for_update(bundle.id)
            for offer in bundle_offers:
                if offer.user:
                    self.offer_service.unfreeze_balance(offer.user, offer.price)
                await self.offer_log_repo.create_event(
                    offer_id=None,
                    nft_id=None,
                    actor_user_id=user_id,
                    counterparty_user_id=offer.user_id,
                    bundle_offer_id=offer.id,
                    event_type="refused",
                    amount_nanotons=offer.price,
                    meta={"bundle_id": bundle.id, "reason": "bundle_cancelled"},
                )
                await self.session.delete(offer)

            bundle.status = "cancelled"
            bundle.cancelled_at = datetime.utcnow()

            for item in bundle.items:
                if item.nft:
                    item.nft.active_bundle_id = None

            await uow.commit()

        logger.info(
            "Bundle cancelled", extra={"bundle_id": bundle_id, "user_id": user_id, "item_count": len(bundle.items)}
        )
        return {"success": True, "bundle_id": bundle.id, "status": bundle.status}


class BuyBundleUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BundleRepository(session)
        self.nft_service = NFTService(self.repo)

    async def execute(self, user_id: int, request: BuyBundleRequest) -> dict:
        from app.db.models import NFTDeal, User

        async with redis_lock(f"bundle:state:{request.bundle_id}", timeout=10), get_uow(self.session) as uow:
            bundle = await self.repo.get_bundle_for_update(request.bundle_id)
            if not bundle:
                raise BundleNotFoundError(request.bundle_id)
            if bundle.status != "active":
                raise BundleNotActiveError(request.bundle_id)
            if bundle.seller_id == user_id:
                raise BundlePermissionDeniedError(request.bundle_id)

            # Авто-отмена офферов на бандл (разморозка средств)
            bundle_offer_repo = BundleOfferRepository(self.session)
            offer_service = OfferService(bundle_offer_repo)
            offer_log_repo = OfferEventLogRepository(self.session)
            bundle_offers = await bundle_offer_repo.list_offers_for_bundle_for_update(bundle.id)
            for offer in bundle_offers:
                if offer.user:
                    offer_service.unfreeze_balance(offer.user, offer.price)
                await offer_log_repo.create_event(
                    offer_id=None,
                    nft_id=None,
                    actor_user_id=user_id,
                    counterparty_user_id=offer.user_id,
                    bundle_offer_id=offer.id,
                    event_type="refused",
                    amount_nanotons=offer.price,
                    meta={"bundle_id": bundle.id, "reason": "bundle_sold"},
                )
                await self.session.delete(offer)

            buyer = await self.session.get(User, user_id)
            seller = await self.session.get(User, bundle.seller_id)

            # проверка NFT в бандле
            nfts = [item.nft for item in bundle.items if item.nft]
            if not nfts:
                raise InvalidBundleItemsError("Bundle has no NFTs", [])
            for nft in nfts:
                if nft.active_bundle_id != bundle.id or nft.account_id is not None:
                    raise InvalidBundleItemsError("NFT not available for bundle purchase", [nft.id])

            price = bundle.price_nanotons
            if buyer.market_balance < price:
                from app.modules.nft.exceptions import InsufficientBalanceError

                raise InsufficientBalanceError(required=price, available=buyer.market_balance)

            commission, seller_amount = self.nft_service.calculate_commission(price)
            buyer.market_balance -= price
            seller.market_balance += seller_amount

            deal_ids: list[int] = []
            count = len(nfts)
            base_price = price // count
            remainder = price - base_price * count

            for idx, nft in enumerate(nfts):
                deal_price = base_price + (remainder if idx == 0 else 0)
                deal = NFTDeal(gift_id=nft.gift_id, seller_id=bundle.seller_id, buyer_id=buyer.id, price=deal_price)
                self.session.add(deal)
                await self.session.flush()
                deal_ids.append(deal.id)

                nft.user_id = buyer.id
                nft.price = None
                nft.active_bundle_id = None

            bundle.status = "sold"
            await uow.commit()

        logger.info(
            "Bundle purchased",
            extra={
                "bundle_id": bundle.id,
                "buyer_id": buyer.id,
                "seller_id": seller.id,
                "price": price,
                "commission": commission,
            },
        )
        return {
            "success": True,
            "bundle_id": bundle.id,
            "price_ton": price / 1e9,
            "commission_nanotons": commission,
            "commission_ton": commission / 1e9,
            "buyer_id": buyer.id,
            "seller_id": seller.id,
            "deal_ids": deal_ids,
        }


class CreateBundleOfferUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BundleRepository(session)
        self.offer_repo = BundleOfferRepository(session)
        self.log_repo = OfferEventLogRepository(session)
        self.offer_service = OfferService(self.offer_repo)

    async def execute(self, user_id: int, request: BundleOfferRequest) -> dict:
        from app.db.models import User

        price = int(request.price_ton * 1e9)
        async with redis_lock(f"bundle:state:{request.bundle_id}", timeout=10), get_uow(self.session) as uow:
            bundle = await self.offer_repo.get_bundle_for_offer(request.bundle_id)
            if not bundle:
                raise BundleNotFoundError(request.bundle_id)
            if bundle.seller_id == user_id:
                raise BundlePermissionDeniedError(request.bundle_id)

            if await self.offer_repo.get_existing_offer(request.bundle_id, user_id):
                raise InvalidBundleItemsError("Offer already exists for bundle", [request.bundle_id])

            min_price = bundle.price_nanotons * MIN_OFFER_PERCENT // 100
            if price < min_price:
                from app.modules.offers.exceptions import OfferPriceTooLowError

                raise OfferPriceTooLowError(price, bundle.price_nanotons, min_percent=50)

            user = await self.session.get(User, user_id)
            self.offer_service.freeze_balance(user, price)

            offer = await self.offer_repo.create_offer(bundle.id, user_id, price)
            await self.log_repo.create_event(
                offer_id=None,
                nft_id=None,
                actor_user_id=user_id,
                counterparty_user_id=bundle.seller_id,
                bundle_offer_id=offer.id,
                event_type="created",
                amount_nanotons=price,
                meta={"bundle_id": bundle.id, "bundle_price": bundle.price_nanotons},
            )

            await uow.commit()

        logger.info(
            "Bundle offer created",
            extra={"bundle_id": bundle.id, "bundle_offer_id": offer.id, "user_id": user_id, "price": price},
        )
        return {"created": True, "bundle_offer_id": offer.id, "frozen_amount": price}