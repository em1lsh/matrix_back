from sqlalchemy import asc, desc, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Gift, NFT, NFTBundle, NFTBundleItem, NFTBundleOffer

from .schemas import BundleFilter


class BundleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_bundle(self, seller_id: int, price_nanotons: int) -> NFTBundle:
        bundle = NFTBundle(seller_id=seller_id, price_nanotons=price_nanotons, status="active")
        self.session.add(bundle)
        await self.session.flush()
        await self.session.refresh(bundle)
        return bundle

    async def add_items(self, bundle_id: int, nft_ids: list[int]) -> list[NFTBundleItem]:
        items: list[NFTBundleItem] = []
        for nft_id in nft_ids:
            item = NFTBundleItem(bundle_id=bundle_id, nft_id=nft_id)
            self.session.add(item)
            items.append(item)
        await self.session.flush()
        return items

    async def get_bundle_for_update(self, bundle_id: int) -> NFTBundle | None:
        result = await self.session.execute(
            select(NFTBundle)
            .where(NFTBundle.id == bundle_id)
            .options(
                selectinload(NFTBundle.items)
                .selectinload(NFTBundleItem.nft)
                .selectinload(NFT.gift)
            )
            .with_for_update()
        )
        return result.unique().scalar_one_or_none()

    async def get_bundle_with_items(self, bundle_id: int) -> NFTBundle | None:
        result = await self.session.execute(
            select(NFTBundle)
            .where(NFTBundle.id == bundle_id)
            .options(
                selectinload(NFTBundle.items)
                .selectinload(NFTBundleItem.nft)
                .selectinload(NFT.gift)
            )
        )
        return result.unique().scalar_one_or_none()

    async def list_active_bundles(self, filter: BundleFilter) -> tuple[list[NFTBundle], int]:
        query = select(NFTBundle).where(NFTBundle.status == "active")
        count_q = select(func.count()).select_from(NFTBundle).where(NFTBundle.status == "active")

        # price_min/max по цене бандла
        if filter.price_min is not None:
            query = query.where(NFTBundle.price_nanotons >= int(filter.price_min * 1e9))
            count_q = count_q.where(NFTBundle.price_nanotons >= int(filter.price_min * 1e9))
        if filter.price_max is not None:
            query = query.where(NFTBundle.price_nanotons <= int(filter.price_max * 1e9))
            count_q = count_q.where(NFTBundle.price_nanotons <= int(filter.price_max * 1e9))

        # EXISTS по items->nft->gift
        exists_conditions = []
        if filter.titles:
            exists_conditions.append(Gift.title.in_(filter.titles))
        if filter.models:
            exists_conditions.append(Gift.model_name.in_(filter.models))
        if filter.patterns:
            exists_conditions.append(Gift.pattern_name.in_(filter.patterns))
        if filter.backdrops:
            exists_conditions.append(Gift.backdrop_name.in_(filter.backdrops))
        if filter.num is not None:
            exists_conditions.append(Gift.num == filter.num)
        if filter.num_min is not None:
            exists_conditions.append(Gift.num >= filter.num_min)
        if filter.num_max is not None:
            exists_conditions.append(Gift.num <= filter.num_max)

        if exists_conditions:
            exists_subq = (
                select(1)
                .select_from(NFTBundleItem)
                .join(NFT, NFT.id == NFTBundleItem.nft_id)
                .join(Gift, Gift.id == NFT.gift_id)
                .where(NFTBundleItem.bundle_id == NFTBundle.id, *exists_conditions)
            )
            query = query.where(exists(exists_subq))
            count_q = count_q.where(exists(exists_subq))

        total = await self.session.scalar(count_q) or 0

        # сортировки с агрегацией по элементам
        sort = filter.sort or "created_at/desc"
        field, direction = sort.split("/")
        is_asc = direction == "asc"

        if field in {"num", "model_rarity", "pattern_rarity", "backdrop_rarity"}:
            col = {
                "num": Gift.num,
                "model_rarity": Gift.model_rarity,
                "pattern_rarity": Gift.pattern_rarity,
                "backdrop_rarity": Gift.backdrop_rarity,
            }[field]

            agg_col = func.min(col) if is_asc else func.max(col)

            agg_subq = (
                select(NFTBundleItem.bundle_id.label("b_id"), agg_col.label("agg"))
                .select_from(NFTBundleItem)
                .join(NFT, NFT.id == NFTBundleItem.nft_id)
                .join(Gift, Gift.id == NFT.gift_id)
                .group_by(NFTBundleItem.bundle_id)
                .subquery()
            )

            query = query.join(agg_subq, agg_subq.c.b_id == NFTBundle.id)

            order_col = agg_subq.c.agg
            query = query.order_by(asc(order_col) if is_asc else desc(order_col), desc(NFTBundle.id))
        elif field == "price":
            query = query.order_by(
                asc(NFTBundle.price_nanotons) if is_asc else desc(NFTBundle.price_nanotons),
                desc(NFTBundle.id),
            )
        else:  # created_at
            query = query.order_by(asc(NFTBundle.created_at) if is_asc else desc(NFTBundle.created_at), desc(NFTBundle.id))

        query = query.options(
            selectinload(NFTBundle.items).selectinload(NFTBundleItem.nft).selectinload(NFT.gift)
        )

        query = query.offset(filter.offset).limit(filter.limit)

        result = await self.session.execute(query)
        items = list(result.unique().scalars().all())

        return items, total

    async def list_user_bundles(self, seller_id: int, filter: BundleFilter) -> tuple[list[NFTBundle], int]:
        query = select(NFTBundle).where(NFTBundle.seller_id == seller_id)
        count_q = select(func.count()).select_from(NFTBundle).where(NFTBundle.seller_id == seller_id)

        if filter.price_min is not None:
            query = query.where(NFTBundle.price_nanotons >= int(filter.price_min * 1e9))
            count_q = count_q.where(NFTBundle.price_nanotons >= int(filter.price_min * 1e9))
        if filter.price_max is not None:
            query = query.where(NFTBundle.price_nanotons <= int(filter.price_max * 1e9))
            count_q = count_q.where(NFTBundle.price_nanotons <= int(filter.price_max * 1e9))

        exists_conditions = []
        if filter.titles:
            exists_conditions.append(Gift.title.in_(filter.titles))
        if filter.models:
            exists_conditions.append(Gift.model_name.in_(filter.models))
        if filter.patterns:
            exists_conditions.append(Gift.pattern_name.in_(filter.patterns))
        if filter.backdrops:
            exists_conditions.append(Gift.backdrop_name.in_(filter.backdrops))
        if filter.num is not None:
            exists_conditions.append(Gift.num == filter.num)
        if filter.num_min is not None:
            exists_conditions.append(Gift.num >= filter.num_min)
        if filter.num_max is not None:
            exists_conditions.append(Gift.num <= filter.num_max)

        if exists_conditions:
            exists_subq = (
                select(1)
                .select_from(NFTBundleItem)
                .join(NFT, NFT.id == NFTBundleItem.nft_id)
                .join(Gift, Gift.id == NFT.gift_id)
                .where(NFTBundleItem.bundle_id == NFTBundle.id, *exists_conditions)
            )
            query = query.where(exists(exists_subq))
            count_q = count_q.where(exists(exists_subq))

        total = await self.session.scalar(count_q) or 0

        sort = filter.sort or "created_at/desc"
        field, direction = sort.split("/")
        is_asc = direction == "asc"

        if field in {"num", "model_rarity", "pattern_rarity", "backdrop_rarity"}:
            col = {
                "num": Gift.num,
                "model_rarity": Gift.model_rarity,
                "pattern_rarity": Gift.pattern_rarity,
                "backdrop_rarity": Gift.backdrop_rarity,
            }[field]

            agg_col = func.min(col) if is_asc else func.max(col)

            agg_subq = (
                select(NFTBundleItem.bundle_id.label("b_id"), agg_col.label("agg"))
                .select_from(NFTBundleItem)
                .join(NFT, NFT.id == NFTBundleItem.nft_id)
                .join(Gift, Gift.id == NFT.gift_id)
                .group_by(NFTBundleItem.bundle_id)
                .subquery()
            )

            query = query.join(agg_subq, agg_subq.c.b_id == NFTBundle.id)

            order_col = agg_subq.c.agg
            query = query.order_by(asc(order_col) if is_asc else desc(order_col), desc(NFTBundle.id))
        elif field == "price":
            query = query.order_by(
                asc(NFTBundle.price_nanotons) if is_asc else desc(NFTBundle.price_nanotons),
                desc(NFTBundle.id),
            )
        else:
            query = query.order_by(asc(NFTBundle.created_at) if is_asc else desc(NFTBundle.created_at), desc(NFTBundle.id))

        query = query.options(
            selectinload(NFTBundle.items).selectinload(NFTBundleItem.nft).selectinload(NFT.gift)
        )

        query = query.offset(filter.offset).limit(filter.limit)

        result = await self.session.execute(query)
        items = list(result.unique().scalars().all())

        return items, total


class BundleOfferRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_offers_for_bundle_for_update(self, bundle_id: int) -> list[NFTBundleOffer]:
        """Получить все офферы по бандлу с блокировкой (для cancel/buy)."""
        result = await self.session.execute(
            select(NFTBundleOffer)
            .where(NFTBundleOffer.bundle_id == bundle_id)
            .options(selectinload(NFTBundleOffer.user))
            .order_by(NFTBundleOffer.id)
            .with_for_update()
        )
        return list(result.unique().scalars().all())

    async def get_bundle_for_offer(self, bundle_id: int) -> NFTBundle | None:
        result = await self.session.execute(
            select(NFTBundle)
            .where(NFTBundle.id == bundle_id, NFTBundle.status == "active")
            .options(selectinload(NFTBundle.items).selectinload(NFTBundleItem.nft))
            .with_for_update()
        )
        return result.unique().scalar_one_or_none()

    async def get_existing_offer(self, bundle_id: int, user_id: int) -> NFTBundleOffer | None:
        result = await self.session.execute(
            select(NFTBundleOffer).where(NFTBundleOffer.bundle_id == bundle_id, NFTBundleOffer.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_offer(self, bundle_id: int, user_id: int, price: int) -> NFTBundleOffer:
        offer = NFTBundleOffer(bundle_id=bundle_id, user_id=user_id, price=price)
        self.session.add(offer)
        await self.session.flush()
        await self.session.refresh(offer)
        return offer
