"""Buy Orders модуль - Router"""

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.db import AsyncSession, get_db
from app.db.models import User
from app.modules.buy_orders.schemas import (
    BuyOrderResponse,
    BuyOrdersFilter,
    BuyOrdersListResponse,
    CreateBuyOrderRequest,
    SellToOrderRequest,
    SellToOrderResponse,
)
from app.modules.buy_orders.use_cases import (
    CancelBuyOrderUseCase,
    CreateBuyOrderUseCase,
    ListBuyOrdersUseCase,
    ListMyActiveBuyOrdersUseCase,
    SellToBuyOrderUseCase,
)


router = APIRouter(prefix="/buy-orders", tags=["BuyOrders"])


@router.post("", response_model=BuyOrderResponse)
async def create_buy_order(
    payload: CreateBuyOrderRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    создать ордер на покупку подарка.
    - ссоздает активный ордер с указанными фильтрами модели/паттерна/фонового оформления
    - возвращает созданный ордер с пересчитанной ценой в TON и остатком количества
    """
    use_case = CreateBuyOrderUseCase(session)
    return await use_case.execute(user.id, payload)


@router.delete("/{order_id}")
async def cancel_buy_order(
    order_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    отменить свой ордер.
    - Размораживает оставшиеся средства и переводит их обратно в market_balance
    - Помечает ордер как CANCELLED
    """
    use_case = CancelBuyOrderUseCase(session)
    return await use_case.execute(order_id, user.id)


@router.post("/list", response_model=BuyOrdersListResponse)
async def list_buy_orders(
    payload: BuyOrdersFilter,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    список ордеров на покупку.

    - titles/models/patterns/backdrops: точное совпадение по характеристикам подарка
    - price_min/price_max: диапазон цены в TON
    - status: active/cancelled/filled
    - sort: created_at/asc|desc или price/asc|desc
    - limit/offset: пагинация (limit до 100)
    """
    use_case = ListBuyOrdersUseCase(session)
    return await use_case.execute(payload)


@router.post("/my/active", response_model=BuyOrdersListResponse)
async def list_my_active_orders(
    payload: BuyOrdersFilter,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    получить свои активные ордера.
    - поддерживает те же фильтры, сортировку и пагинацию, что и общий список
    """
    use_case = ListMyActiveBuyOrdersUseCase(session)
    return await use_case.execute(user.id, payload)


@router.post("/{order_id}/sell", response_model=SellToOrderResponse)
async def sell_to_buy_order(
    order_id: int,
    payload: SellToOrderRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    продать свой NFT в выбранный ордер.
    - принимает nft_id
    - совершает сделку по лимитной цене ордера, рассчитывает комиссию и сумму продавца
    """
    use_case = SellToBuyOrderUseCase(session)
    return await use_case.execute(order_id, user.id, payload)