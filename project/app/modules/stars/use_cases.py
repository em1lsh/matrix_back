"""Use Cases для модуля stars"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs import settings
from app.db import get_uow
from app.db.models import StarsPurchase
from app.utils.logger import get_logger

from .repository import StarsRepository
from .schemas import *
from .service import StarsService


logger = get_logger(__name__)


class GetStarsPriceUseCase:
    """UseCase: Получить цену звёзд"""

    def __init__(self, session: AsyncSession):
        self.service = StarsService()

    async def execute(self, stars_amount: int) -> StarsPriceResponse:
        """Получить цену звёзд с наценкой"""
        self.service.validate_stars_amount(stars_amount)
        
        price_info = await self.service.get_stars_price_with_markup(stars_amount)
        
        return StarsPriceResponse(**price_info)


class BuyStarsUseCase:
    """UseCase: Купить звёзды"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = StarsRepository(session)
        self.service = StarsService()

    async def execute(
        self, 
        user_id: int, 
        recipient_username: str, 
        stars_amount: int
    ) -> BuyStarsResponse:
        """
        Купить звёзды для указанного пользователя.
        
        1. Валидация данных
        2. Получение цены с наценкой
        3. Проверка баланса пользователя
        4. Создание записи о покупке
        5. Списание средств
        6. Покупка через Fragment API
        7. Обновление статуса
        """
        async with get_uow(self.session) as uow:
            # 1. Валидация
            username = self.service.validate_username(recipient_username)
            self.service.validate_stars_amount(stars_amount)

            # 2. Получить пользователя
            user = await self.repo.get_user_by_id(user_id)
            if not user:
                from app.modules.users.exceptions import UserNotFoundError
                raise UserNotFoundError(user_id)

            # 3. Получить цену с наценкой
            price_info = await self.service.get_stars_price_with_markup(stars_amount)
            required_nanotons = price_info["final_price_nanotons"]

            # 4. Проверить баланс
            self.service.validate_user_balance(user, required_nanotons)

            # 5. Создать запись о покупке
            purchase = StarsPurchase(
                user_id=user_id,
                recipient_username=username,
                stars_amount=stars_amount,
                price_nanotons=required_nanotons,
                fragment_cost_ton=price_info["fragment_price_ton"],
                status="pending"
            )
            self.session.add(purchase)
            await self.session.flush()  # Получить ID

            # 6. Списать средства
            user.market_balance -= required_nanotons

            try:
                # 7. Получить банк-аккаунт для покупки
                from app.db.models import Account
                from app.account.account import Account as AccountClass
                
                bank_account = await self.session.execute(
                    select(Account).where(Account.telegram_id == settings.bank_account)
                )
                bank_account = bank_account.scalar_one_or_none()
                
                if not bank_account:
                    raise Exception("Bank account not found")

                # 8. Купить через Fragment API от имени банка
                fragment_result = await self.service.buy_stars_via_fragment(
                    username, stars_amount, bank_account
                )

                # 9. Обновить статус успешной покупки
                purchase.status = "completed"
                # Fragment API возвращает "id" (UUID), а не "transaction_id"
                purchase.fragment_tx_id = fragment_result.get("id")
                # Fragment возвращает "ton_price" как строку
                ton_price_str = fragment_result.get("ton_price")
                if ton_price_str:
                    try:
                        purchase.fragment_cost_ton = float(ton_price_str)
                    except (ValueError, TypeError):
                        purchase.fragment_cost_ton = price_info["fragment_price_ton"]
                else:
                    purchase.fragment_cost_ton = price_info["fragment_price_ton"]

                await uow.commit()

                logger.info(
                    "Stars purchased successfully",
                    extra={
                        "purchase_id": purchase.id,
                        "user_id": user_id,
                        "recipient": username,
                        "stars": stars_amount,
                        "price_ton": required_nanotons / 1e9,
                        "fragment_tx_id": purchase.fragment_tx_id
                    }
                )

                return BuyStarsResponse(
                    success=True,
                    purchase_id=purchase.id,
                    stars_amount=stars_amount,
                    recipient_username=username,
                    price_paid_ton=required_nanotons / 1e9,
                    fragment_tx_id=purchase.fragment_tx_id,
                    status="completed"
                )

            except Exception as e:
                # 10. Обработка ошибки Fragment API
                purchase.status = "failed"
                purchase.error_message = str(e)[:500]

                # Возвращаем средства пользователю
                user.market_balance += required_nanotons

                await uow.commit()

                logger.error(
                    "Stars purchase failed",
                    extra={
                        "purchase_id": purchase.id,
                        "user_id": user_id,
                        "recipient": username,
                        "stars": stars_amount,
                        "error": str(e)
                    }
                )

                # Пробрасываем исключение чтобы вернуть правильный HTTP статус
                from app.shared.exceptions import AppException
                if isinstance(e, AppException):
                    raise
                # Оборачиваем неизвестные ошибки
                from .exceptions import FragmentAPIError
                raise FragmentAPIError(str(e))


class GetUserStarsPurchasesUseCase:
    """UseCase: Получить покупки звёзд пользователя"""

    def __init__(self, session: AsyncSession):
        self.repo = StarsRepository(session)

    async def execute(
        self, 
        user_id: int, 
        limit: int = 20, 
        offset: int = 0
    ) -> StarsPurchaseListResponse:
        """Получить историю покупок звёзд пользователя"""
        purchases, total = await self.repo.get_user_purchases(user_id, limit, offset)

        return StarsPurchaseListResponse(
            purchases=[StarsPurchaseResponse.model_validate(p) for p in purchases],
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(purchases)) < total
        )


class GetPremiumPriceUseCase:
    """UseCase: Получить цену Telegram Premium"""

    def __init__(self, session: AsyncSession):
        self.service = StarsService()

    async def execute(self, months: int) -> PremiumPriceResponse:
        """Получить цену премиума с наценкой"""
        price_info = await self.service.get_premium_price_with_markup(months)
        return PremiumPriceResponse(**price_info)


class BuyPremiumUseCase:
    """UseCase: Купить Telegram Premium через Fragment API"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = StarsRepository(session)
        self.service = StarsService()

    async def execute(
        self,
        user_id: int,
        username: str,
        months: int,
        show_sender: bool = False
    ) -> dict:
        """
        Купить Telegram Premium подписку через Fragment API.
        
        1. Валидация данных
        2. Получение цены с наценкой
        3. Проверка баланса пользователя
        4. Создание записи о покупке
        5. Списание средств
        6. Покупка через Fragment API
        7. Обновление статуса
        """
        import json
        from app.integrations.fragment.integration import FragmentIntegration
        from app.db.models.stars import PremiumPurchase
        from app.db import get_uow
        from app.modules.stars.exceptions import PremiumMonthsError
        from app.shared.exceptions import AppException
        
        # Валидация months
        if months not in (3, 6, 12):
            raise PremiumMonthsError(months)
        
        # Убираем @ если есть
        if username.startswith("@"):
            username = username[1:]
        
        async with get_uow(self.session) as uow:
            # 1. Получить пользователя
            user = await self.repo.get_user_by_id(user_id)
            if not user:
                from app.modules.users.exceptions import UserNotFoundError
                raise UserNotFoundError(user_id)
            
            # 2. Получить цену с наценкой
            price_info = await self.service.get_premium_price_with_markup(months)
            required_nanotons = price_info["final_price_nanotons"]
            
            # 3. Проверить баланс
            self.service.validate_user_balance(user, required_nanotons)
            
            # 4. Создаём запись о покупке
            purchase = PremiumPurchase(
                user_id=user_id,
                recipient_username=username,
                months=months,
                show_sender=show_sender,
                price_nanotons=required_nanotons,
                status="pending"
            )
            self.session.add(purchase)
            await self.session.flush()
            
            # 5. Списать средства
            user.market_balance -= required_nanotons
            
            try:
                # 6. Покупка через Fragment API
                fragment = FragmentIntegration()
                result = await fragment.buy_premium(
                    username=username,
                    months=months,
                    show_sender=show_sender
                )
                
                # 7. Обновляем запись успешной покупки
                purchase.status = "completed"
                purchase.fragment_tx_id = result.get("id")
                purchase.ton_price = result.get("ton_price")
                purchase.ref_id = result.get("ref_id")
                purchase.fragment_response = json.dumps(result)[:2000]
                
                await uow.commit()
                
                logger.info(
                    "Premium purchase completed",
                    extra={
                        "purchase_id": purchase.id,
                        "user_id": user_id,
                        "username": username,
                        "months": months,
                        "price_ton": required_nanotons / 1e9,
                        "fragment_tx_id": purchase.fragment_tx_id
                    }
                )
                return result
                
            except Exception as e:
                # 8. Обработка ошибки - возвращаем средства
                purchase.status = "failed"
                purchase.error_message = str(e)[:500]
                user.market_balance += required_nanotons
                
                await uow.commit()
                
                logger.error(
                    "Premium purchase failed",
                    extra={
                        "purchase_id": purchase.id,
                        "user_id": user_id,
                        "username": username,
                        "months": months,
                        "error": str(e)
                    }
                )
                
                # Пробрасываем исключение
                if isinstance(e, AppException):
                    raise
                from .exceptions import FragmentAPIError
                raise FragmentAPIError(str(e))


class GetFragmentUserInfoUseCase:
    """UseCase: Получить информацию о пользователе через Fragment"""

    def __init__(self, session: AsyncSession):
        self.service = StarsService()

    async def execute(self, username: str) -> FragmentUserInfoResponse:
        """Получить информацию о пользователе из Fragment API"""
        normalized_username = self.service.validate_username(username)
        user_info = await self.service.get_fragment_user_info(normalized_username)
        return FragmentUserInfoResponse(username=normalized_username, data=user_info)
