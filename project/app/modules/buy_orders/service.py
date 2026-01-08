"""Buy Orders модуль - Service"""

from app.configs import settings
from app.db.models import BuyOrder, BuyOrderDeal, BuyOrderDealSource, BuyOrderStatus, NFT, NFTDeal, User
from app.modules.buy_orders.constants import BUY_ORDER_SORT_OPTIONS, BuyOrderDealSourceEnum
from app.modules.buy_orders.exceptions import InsufficientBalanceError
from app.utils.logger import get_logger
from app.modules.promotion.repository import PromotionRepository


logger = get_logger(__name__)


class BuyOrderService:
    """Бизнес-логика ордеров"""

    def __init__(self, repository):
        self.repo = repository

    def validate_create_order(self, user: User, reserve: int) -> None:
        if user.market_balance < reserve:
            raise InsufficientBalanceError(required=reserve, available=user.market_balance)

    def validate_sort(self, sort: str) -> None:
        if sort not in BUY_ORDER_SORT_OPTIONS:
            from app.shared.exceptions import AppException

            raise AppException(
                f"Unsupported sort: {sort}",
                status_code=400,
                error_code="INVALID_SORT",
            )

    def freeze_for_order(self, user: User, amount: int) -> None:
        user.market_balance -= amount
        user.frozen_balance += amount
        logger.info(
            "Balance frozen for buy order",
            extra={
                "user_id": user.id,
                "amount": amount,
                "new_market_balance": user.market_balance,
                "new_frozen_balance": user.frozen_balance,
            },
        )

    def unfreeze_order_remaining(self, user: User, order: BuyOrder) -> int:
        refunded = order.frozen_amount
        user.frozen_balance -= refunded
        user.market_balance += refunded
        order.frozen_amount = 0
        order.status = BuyOrderStatus.CANCELLED
        logger.info(
            "Order cancelled and balance unfrozen",
            extra={
                "user_id": user.id,
                "order_id": order.id,
                "refunded": refunded,
                "market_balance": user.market_balance,
                "frozen_balance": user.frozen_balance,
            },
        )
        return refunded

    async def execute_order_fill(
        self,
        order: BuyOrder,
        nft: NFT,
        buyer: User,
        seller: User,
        execution_price: int,
        source: BuyOrderDealSourceEnum,
    ) -> BuyOrderDeal:
        reserved_price = order.price_limit
        refund = reserved_price - execution_price if execution_price < reserved_price else 0

        commission = self.calculate_commission(execution_price)
        seller_amount = execution_price - commission

        buyer.frozen_balance -= reserved_price
        buyer.market_balance += refund
        seller.market_balance += seller_amount

        old_owner = nft.user_id
        nft.user_id = buyer.id
        nft.price = None

        promotion_repo = PromotionRepository(self.repo.session)
        await promotion_repo.deactivate_promotion(nft.id)

        nft_deal = NFTDeal(
            gift_id=nft.gift_id,
            seller_id=old_owner,
            buyer_id=buyer.id,
            price=execution_price,
        )
        self.repo.session.add(nft_deal)
        await self.repo.session.flush()

        order.quantity_remaining -= 1
        order.frozen_amount -= reserved_price
        if order.quantity_remaining == 0:
            order.status = BuyOrderStatus.FILLED

        buy_order_deal = BuyOrderDeal(
            order_id=order.id,
            nft_id=nft.id,
            gift_id=nft.gift_id,
            buyer_id=buyer.id,
            seller_id=seller.id,
            reserved_unit_price=reserved_price,
            execution_price=execution_price,
            commission=commission,
            seller_amount=seller_amount,
            source=source,
            nft_deal_id=nft_deal.id,
        )
        self.repo.session.add(buy_order_deal)

        logger.info(
            "Buy order filled",
            extra={
                "order_id": order.id,
                "nft_id": nft.id,
                "buyer_id": buyer.id,
                "seller_id": seller.id,
                "execution_price": execution_price,
                "refund": refund,
                "commission": commission,
                "seller_amount": seller_amount,
                "source": source,
            },
        )

        return buy_order_deal

    def calculate_commission(self, price: int) -> int:
        commission = int(price * settings.market_comission / 100)
        logger.debug("Commission calculated", extra={"price": price, "commission": commission})
        return commission
