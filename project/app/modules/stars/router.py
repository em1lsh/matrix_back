"""API роуты для модуля stars"""

from fastapi import APIRouter, Depends, Query

from app.api.auth import get_current_user
from app.db import AsyncSession, get_db
from app.db.models import User

from .schemas import *
from .use_cases import *


router = APIRouter(prefix="/stars", tags=["Stars"])


@router.get("/price", response_model=StarsPriceResponse)
async def get_stars_price(
    stars_amount: int = Query(..., ge=1, le=1000000, description="Количество звёзд"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить цену звёзд с наценкой маркета.
    
    - **stars_amount**: Количество звёзд (1-1000000)
    
    Возвращает цену Fragment + наценку маркета.
    """
    use_case = GetStarsPriceUseCase(session)
    return await use_case.execute(stars_amount)


@router.post("/buy", response_model=BuyStarsResponse)
async def buy_stars(
    request: BuyStarsRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Купить звёзды для указанного пользователя.
    
    - **recipient_username**: Username получателя (с @ или без)
    - **stars_amount**: Количество звёзд (1-1000000)
    
    Списывает TON с баланса пользователя и покупает звёзды через Fragment API.
    """
    use_case = BuyStarsUseCase(session)
    return await use_case.execute(
        user_id=current_user.id,
        recipient_username=request.recipient_username,
        stars_amount=request.stars_amount
    )


@router.get("/purchases", response_model=StarsPurchaseListResponse)
async def get_my_stars_purchases(
    limit: int = Query(20, ge=1, le=100, description="Количество записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Получить историю покупок звёзд текущего пользователя.
    
    - **limit**: Количество записей (1-100)
    - **offset**: Смещение для пагинации
    """
    use_case = GetUserStarsPurchasesUseCase(session)
    return await use_case.execute(current_user.id, limit, offset)


@router.get("/premium-price", response_model=PremiumPriceResponse)
async def get_premium_price(
    months: int = Query(..., description="Количество месяцев (3, 6 или 12)"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить цену Telegram Premium с наценкой маркета.
    
    - **months**: Количество месяцев (3, 6 или 12)
    
    Возвращает цену Fragment + наценку маркета.
    """
    use_case = GetPremiumPriceUseCase(session)
    return await use_case.execute(months)


@router.get("/user-info", response_model=FragmentUserInfoResponse)
async def get_fragment_user_info(
    username: str = Query(..., min_length=5, max_length=32, description="Telegram username (с @ или без)"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить информацию о пользователе через Fragment API.
    
    - **username**: Telegram username (с @ или без)
    """
    use_case = GetFragmentUserInfoUseCase(session)
    return await use_case.execute(username)


@router.post("/buy-premium", response_model=BuyPremiumResponse)
async def buy_premium(
    request: BuyPremiumRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Купить Telegram Premium подписку через Fragment API.
    
    Покупает Premium подписку для указанного пользователя.
    Списывает TON с баланса пользователя.
    
    **Параметры:**
    - **username**: Telegram username получателя (без @), паттерн: [a-zA-Z][a-zA-Z0-9_]{2,31}$
    - **months**: Длительность подписки (3, 6 или 12 месяцев)
    - **show_sender**: Показывать отправителя (default: false)
    
    **Error codes от Fragment:**
    - 0 - General error code
    - 10 - TON Network error code
    - 11 - KYC is needed for specified account
    - 12 - TON Network connection error
    - 13 - General TON / Telegram error
    - 20 - Recipient username was not found on Fragment
    
    **Внимание:** Операция списывает реальные средства!
    """
    use_case = BuyPremiumUseCase(session)
    return await use_case.execute(
        user_id=current_user.id,
        username=request.username,
        months=request.months,
        show_sender=request.show_sender
    )
