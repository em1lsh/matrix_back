"""Use Cases модуля продвижения NFT"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_uow
from app.utils.logger import get_logger
from app.modules.unified.schemas import GiftResponse, MarketInfo, SalingItem, UnifiedFilter, UnifiedResponse

from .exceptions import NFTNotFoundError, PromotionAlreadyActiveError
from .repository import PromotionRepository
from .schemas import (
    PromotionCalculationResponse,
    PromotionOperationResponse,
    PromotionResponse,
)
from .service import PromotionService

logger = get_logger(__name__)


class CalculatePromotionCostUseCase:
    """UseCase: Рассчитать стоимость продвижения"""

    def __init__(self):
        self.service = PromotionService()

    async def execute(self, days: int) -> PromotionCalculationResponse:
        """Выполнить расчет стоимости"""
        final_cost_nanotons, discount_percent = self.service.calculate_promotion_cost(days)
        
        # Базовая стоимость без скидки
        base_cost_nanotons = self.service.daily_cost_nanotons * days
        
        # Конвертируем в TON
        base_cost_ton = base_cost_nanotons / 1e9
        final_cost_ton = final_cost_nanotons / 1e9
        savings_ton = (base_cost_nanotons - final_cost_nanotons) / 1e9
        
        return PromotionCalculationResponse(
            days=days,
            base_cost_ton=base_cost_ton,
            discount_percent=discount_percent * 100,  # В процентах
            final_cost_ton=final_cost_ton,
            savings_ton=savings_ton,
        )


class PromoteNFTUseCase:
    """UseCase: Продвинуть NFT"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PromotionRepository(session)
        self.service = PromotionService()

    async def execute(self, nft_id: int, user_id: int, days: int) -> PromotionOperationResponse:
        """Выполнить продвижение NFT"""
        async with get_uow(self.session) as uow:
            # 1. Получить NFT
            nft = await self.repo.get_nft_by_id(nft_id)
            if not nft:
                raise NFTNotFoundError(nft_id)

            # 2. Проверить владельца
            self.service.validate_nft_ownership(nft, user_id)

            # 3. Проверить, что нет активного продвижения
            existing_promotion = await self.repo.get_active_promotion(nft_id)
            if existing_promotion:
                raise PromotionAlreadyActiveError(nft_id)

            # 4. Получить пользователя
            user = await self.repo.get_user_by_id(user_id)

            # 5. Рассчитать стоимость
            cost_nanotons, _ = self.service.calculate_promotion_cost(days)

            # 6. Проверить баланс
            self.service.validate_user_balance(user, cost_nanotons)

            # 7. Рассчитать время окончания
            ends_at = self.service.calculate_promotion_end_time(days)

            # 8. Создать продвижение
            promotion = await self.repo.create_promotion(
                nft_id=nft_id,
                user_id=user_id,
                ends_at=ends_at,
                total_costs=cost_nanotons,
            )

            # 9. Списать средства
            user.market_balance -= cost_nanotons

            await uow.commit()

            logger.info(
                "NFT promotion created successfully",
                extra={
                    "nft_id": nft_id,
                    "user_id": user_id,
                    "days": days,
                    "cost_ton": cost_nanotons / 1e9,
                    "ends_at": ends_at,
                },
            )

            return PromotionOperationResponse(
                success=True,
                promotion=PromotionResponse(
                    id=promotion.id,
                    nft_id=promotion.nft_id,
                    user_id=promotion.user_id,
                    created_at=promotion.created_at,
                    ends_at=promotion.ends_at,
                    total_costs_ton=promotion.total_costs / 1e9,
                    is_active=promotion.is_active,
                ),
                cost_ton=cost_nanotons / 1e9,
                new_balance_ton=user.market_balance / 1e9,
            )


class ExtendPromotionUseCase:
    """UseCase: Продлить продвижение NFT"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PromotionRepository(session)
        self.service = PromotionService()

    async def execute(self, nft_id: int, user_id: int, days: int) -> PromotionOperationResponse:
        """Выполнить продление продвижения"""
        async with get_uow(self.session) as uow:
            # 1. Получить NFT
            nft = await self.repo.get_nft_by_id(nft_id)
            if not nft:
                raise NFTNotFoundError(nft_id)

            # 2. Проверить владельца
            self.service.validate_nft_ownership(nft, user_id)

            # 3. Получить активное продвижение
            promotion = await self.repo.get_active_promotion(nft_id)
            if not promotion:
                # Если нет активного продвижения, создаем новое
                return await PromoteNFTUseCase(self.session).execute(nft_id, user_id, days)

            # 4. Получить пользователя
            user = await self.repo.get_user_by_id(user_id)

            # 5. Рассчитать стоимость продления
            cost_nanotons, _ = self.service.calculate_promotion_cost(days)

            # 6. Проверить баланс
            self.service.validate_user_balance(user, cost_nanotons)

            # 7. Рассчитать новое время окончания
            new_ends_at = self.service.calculate_promotion_end_time(days, promotion.ends_at)

            # 8. Продлить продвижение
            promotion = await self.repo.extend_promotion(
                promotion=promotion,
                new_ends_at=new_ends_at,
                additional_cost=cost_nanotons,
            )

            # 9. Списать средства
            user.market_balance -= cost_nanotons

            await uow.commit()

            logger.info(
                "NFT promotion extended successfully",
                extra={
                    "nft_id": nft_id,
                    "user_id": user_id,
                    "days": days,
                    "cost_ton": cost_nanotons / 1e9,
                    "new_ends_at": new_ends_at,
                },
            )

            return PromotionOperationResponse(
                success=True,
                promotion=PromotionResponse(
                    id=promotion.id,
                    nft_id=promotion.nft_id,
                    user_id=promotion.user_id,
                    created_at=promotion.created_at,
                    ends_at=promotion.ends_at,
                    total_costs_ton=promotion.total_costs / 1e9,
                    is_active=promotion.is_active,
                ),
                cost_ton=cost_nanotons / 1e9,
                new_balance_ton=user.market_balance / 1e9,
            )

class GetPromotedNFTsUseCase:
    """UseCase: Получить список активных продвинутых NFT"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PromotionRepository(session)

    async def execute(self, filter: UnifiedFilter) -> UnifiedResponse:
        """Выполнить"""
        limit = min(filter.limit, 10)
        items_db, total = await self.repo.get_active_promoted_nfts(filter, limit, filter.offset)
        items = self._convert_items(items_db)
        return UnifiedResponse(items=items, total=total)

    @staticmethod
    def _convert_items(items_db) -> list[SalingItem]:
        """Конвертировать внутренние items в unified формат"""
        market_info = MarketInfo(id="internal", title="Matrix Gifts", logo=None)
        items = []
        for item in items_db:
            gift = item.gift
            items.append(
                SalingItem(
                    id=str(item.id),
                    price=item.price or 0,
                    gift=GiftResponse(
                        id=gift.id if gift else None,
                        image=gift.image if gift else "",
                        num=gift.num if gift else None,
                        title=gift.title if gift else None,
                        model_name=gift.model_name if gift else None,
                        pattern_name=gift.pattern_name if gift else None,
                        backdrop_name=gift.backdrop_name if gift else None,
                        model_rarity=gift.model_rarity if gift else None,
                        pattern_rarity=gift.pattern_rarity if gift else None,
                        backdrop_rarity=gift.backdrop_rarity if gift else None,
                    ),
                    market=market_info,
                )
            )
        return items