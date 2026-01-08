from app.api.schemas.base import GiftResponse
from app.db.models import NFTBundle, NFTBundleItem

from .schemas import BundleItemResponse, BundleResponse, BundlesListResponse


class BundleService:
    @staticmethod
    def to_item_response(item: NFTBundleItem) -> BundleItemResponse:
        gift = item.nft.gift if item.nft else None
        return BundleItemResponse(
            nft_id=item.nft_id,
            gift=GiftResponse.model_validate(gift) if gift else GiftResponse(),
        )

    @classmethod
    def to_bundle_response(cls, bundle: NFTBundle) -> BundleResponse:
        return BundleResponse(
            id=bundle.id,
            seller_id=bundle.seller_id,
            price=bundle.price_nanotons / 1e9,
            status=bundle.status,
            created_at=bundle.created_at,
            items=[cls.to_item_response(item) for item in bundle.items],
        )

    @classmethod
    def to_list_response(cls, bundles: list[NFTBundle], total: int, limit: int, offset: int) -> BundlesListResponse:
        items = [cls.to_bundle_response(bundle) for bundle in bundles]
        return BundlesListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(items)) < total,
        )