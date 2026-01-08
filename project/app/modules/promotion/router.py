"""Роутер модуля продвижения NFT"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.models import User
from app.db import get_db
from app.modules.unified.schemas import UnifiedFilter, UnifiedResponse

from .exceptions import (
    InsufficientBalanceError,
    InvalidPromotionPeriodError,
    NFTNotFoundError,
    NFTNotOwnedError,
    PromotionAlreadyActiveError,
)
from .schemas import (
    ExtendPromotionRequest,
    PromoteNFTRequest,
    PromotionCalculationRequest,
    PromotionCalculationResponse,
    PromotionOperationResponse,
)
from .use_cases import (
    CalculatePromotionCostUseCase,
    ExtendPromotionUseCase,
    GetPromotedNFTsUseCase,
    PromoteNFTUseCase,
)

router = APIRouter(prefix="/promotion", tags=["NFT Promotion"])


@router.post("/calculate", response_model=PromotionCalculationResponse)
async def calculate_promotion_cost(
    request: PromotionCalculationRequest,
    current_user: User = Depends(get_current_user),
) -> PromotionCalculationResponse:
    """
    Рассчитать стоимость продвижения NFT.
    
    - **days**: Количество дней продвижения (1-30)
    
    Возвращает:
    - Базовую стоимость
    - Размер скидки
    - Итоговую стоимость
    - Экономию
    """
    try:
        use_case = CalculatePromotionCostUseCase()
        return await use_case.execute(request.days)
    except InvalidPromotionPeriodError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/promote", response_model=PromotionOperationResponse)
async def promote_nft(
    request: PromoteNFTRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PromotionOperationResponse:
    """
    Продвинуть NFT.
    
    - **nft_id**: ID NFT для продвижения
    - **days**: Количество дней продвижения (1-30)
    
    Требования:
    - NFT должен принадлежать пользователю
    - У пользователя должно быть достаточно средств
    - NFT не должен иметь активного продвижения
    """
    try:
        use_case = PromoteNFTUseCase(session)
        return await use_case.execute(
            nft_id=request.nft_id,
            user_id=current_user.id,
            days=request.days,
        )
    except NFTNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except NFTNotOwnedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except PromotionAlreadyActiveError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except InsufficientBalanceError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e),
        )
    except InvalidPromotionPeriodError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/extend", response_model=PromotionOperationResponse)
async def extend_promotion(
    request: ExtendPromotionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PromotionOperationResponse:
    """
    Продлить продвижение NFT.
    
    - **nft_id**: ID NFT для продления продвижения
    - **days**: Количество дней для продления (1-30)
    
    Если активного продвижения нет, создает новое.
    """
    try:
        use_case = ExtendPromotionUseCase(session)
        return await use_case.execute(
            nft_id=request.nft_id,
            user_id=current_user.id,
            days=request.days,
        )
    except NFTNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except NFTNotOwnedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except InsufficientBalanceError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e),
        )
    except InvalidPromotionPeriodError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

@router.post("/active", response_model=UnifiedResponse)
async def get_active_promotions(
        filter: UnifiedFilter,
        _current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db),
) -> UnifiedResponse:
    """
    Получить список активных продвинутых NFT.

    - Максимум 10 элементов
    - Поддерживает те же фильтры и сортировку, что и unified
    """
    use_case = GetPromotedNFTsUseCase(session)
    return await use_case.execute(filter)