# DDD Architecture - Вертикальные слайсы

## 🎯 Концепция

Вместо горизонтальных слоев (repositories/, services/, use_cases/), используем **вертикальные слайсы** - каждый модуль содержит всё необходимое:

```
app/
├── modules/                    # Bounded Contexts (домены)
│   ├── nft/                   # NFT модуль
│   │   ├── __init__.py
│   │   ├── models.py          # SQLAlchemy модели (если специфичные)
│   │   ├── schemas.py         # Pydantic схемы
│   │   ├── repository.py      # Работа с БД
│   │   ├── service.py         # Бизнес-логика
│   │   ├── use_cases.py       # Оркестрация
│   │   └── router.py          # HTTP endpoints
│   │
│   ├── market/                # Market модуль
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   ├── use_cases.py
│   │   └── router.py
│   │
│   ├── trades/                # Trades модуль
│   ├── offers/                # Offers модуль
│   ├── presale/               # Presale модуль
│   ├── channels/              # Channels модуль
│   ├── auctions/              # Auctions модуль
│   ├── accounts/              # Accounts модуль
│   └── users/                 # Users модуль
│
├── shared/                    # Общие компоненты
│   ├── base_repository.py     # Базовый репозиторий
│   ├── base_service.py        # Базовый сервис
│   ├── pagination.py          # Пагинация
│   └── exceptions.py          # Исключения
│
├── db/                        # Общая БД инфраструктура
│   ├── models/                # Общие модели
│   │   ├── base.py
│   │   └── user.py           # Shared модели
│   └── uow.py                # Unit of Work
│
└── api/                       # API инфраструктура
    ├── dependencies.py        # Общие зависимости
    └── main.py               # Регистрация роутеров
```

## 📦 Структура модуля (на примере NFT)

### app/modules/nft/

```
nft/
├── __init__.py              # Экспорт публичного API модуля
├── schemas.py               # Все Pydantic схемы NFT
├── repository.py            # NFTRepository - работа с БД
├── service.py               # NFTService - бизнес-логика
├── use_cases.py             # Все use cases NFT
└── router.py                # FastAPI роутер
```

## 🔨 Пример реализации: NFT модуль

### 1. schemas.py - Все схемы модуля

```python
"""NFT модуль - Pydantic схемы"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.shared.pagination import PaginationRequest, PaginatedResponse


class GiftResponse(BaseModel):
    """Подарок"""
    id: int
    title: str | None = None
    image: str | None = None
    num: int | None = None
    
    class Config:
        from_attributes = True


class NFTResponse(BaseModel):
    """NFT ответ"""
    id: int
    gift: GiftResponse
    price: float | None = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class SetPriceRequest(BaseModel):
    """Установка цены NFT"""
    nft_id: int = Field(gt=0)
    price_ton: float | None = Field(None, ge=0, le=100000)
    
    @field_validator("price_ton")
    @classmethod
    def validate_price(cls, v: float | None) -> float | None:
        if v is not None and v < 0.1:
            raise ValueError("Минимальная цена 0.1 TON")
        return round(v, 2) if v else None


class BuyRequest(BaseModel):
    """Покупка NFT"""
    nft_id: int = Field(gt=0)


class ReturnRequest(BaseModel):
    """Возврат NFT в Telegram"""
    nft_id: int = Field(gt=0)


class NFTListResponse(PaginatedResponse[NFTResponse]):
    """Список NFT с пагинацией"""
    pass
```

### 2. repository.py - Работа с БД

```python
"""NFT модуль - Repository"""

from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import NFT, NFTDeal
from app.shared.base_repository import BaseRepository
from app.shared.pagination import PaginationRequest


class NFTRepository(BaseRepository[NFT]):
    """Репозиторий NFT"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(NFT, session)
    
    async def get_with_gift(self, nft_id: int) -> Optional[NFT]:
        """Получить NFT с подарком"""
        result = await self.session.execute(
            select(NFT)
            .where(NFT.id == nft_id)
            .options(joinedload(NFT.gift))
        )
        return result.scalar_one_or_none()
    
    async def get_user_nfts(
        self,
        user_id: int,
        pagination: PaginationRequest
    ) -> tuple[list[NFT], int]:
        """Получить NFT пользователя"""
        # Count
        count_query = select(func.count()).select_from(NFT).where(
            NFT.user_id == user_id,
            NFT.account_id.is_(None)
        )
        total = await self.session.scalar(count_query) or 0
        
        # Data
        query = (
            select(NFT)
            .where(NFT.user_id == user_id, NFT.account_id.is_(None))
            .options(joinedload(NFT.gift))
            .offset(pagination.offset)
            .limit(pagination.limit)
            .order_by(NFT.created_at.desc())
        )
        result = await self.session.execute(query)
        items = list(result.unique().scalars().all())
        
        return items, total
    
    async def get_for_purchase(self, nft_id: int) -> Optional[NFT]:
        """Получить NFT для покупки с блокировкой"""
        result = await self.session.execute(
            select(NFT)
            .where(
                NFT.id == nft_id,
                NFT.price.is_not(None),
                NFT.account_id.is_(None)
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()
```

### 3. service.py - Бизнес-логика

```python
"""NFT модуль - Service"""

import logging
from typing import Optional

from app.db.models import NFT, User
from app.exceptions import (
    NFTNotFoundError,
    PermissionDeniedError,
    InsufficientBalanceError,
    ValidationError
)
from app.configs import settings
from .repository import NFTRepository


logger = logging.getLogger(__name__)


class NFTService:
    """Сервис NFT - бизнес-логика"""
    
    def __init__(self, repository: NFTRepository):
        self.repo = repository
    
    def validate_ownership(self, nft: NFT, user_id: int) -> None:
        """Проверка владения"""
        if nft.user_id != user_id:
            raise PermissionDeniedError("NFT", nft.id)
    
    def validate_available(self, nft: NFT) -> None:
        """Проверка доступности"""
        if nft.account_id is not None:
            raise ValidationError("NFT привязан к аккаунту")
    
    def validate_balance(self, buyer: User, nft: NFT) -> None:
        """Проверка баланса"""
        if buyer.market_balance < nft.price:
            raise InsufficientBalanceError(
                required=nft.price,
                available=buyer.market_balance
            )
    
    def calculate_commission(self, price: int) -> tuple[int, int]:
        """Расчет комиссии"""
        commission = round(price / 100 * settings.market_comission)
        seller_amount = price - commission
        return commission, seller_amount
    
    async def set_price(
        self,
        nft_id: int,
        user_id: int,
        price_ton: Optional[float]
    ) -> NFT:
        """Установить цену"""
        nft = await self.repo.get_with_gift(nft_id)
        if not nft:
            raise NFTNotFoundError(nft_id)
        
        self.validate_ownership(nft, user_id)
        self.validate_available(nft)
        
        nft.price = int(price_ton * 1e9) if price_ton else None
        
        logger.info(
            "NFT price updated",
            extra={"nft_id": nft_id, "price_ton": price_ton}
        )
        
        return nft
```

### 4. use_cases.py - Оркестрация

```python
"""NFT модуль - Use Cases"""

import logging
from typing import TypedDict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_uow
from app.shared.pagination import PaginationRequest
from .repository import NFTRepository
from .service import NFTService
from .schemas import NFTResponse, NFTListResponse


logger = logging.getLogger(__name__)


class SetPriceResult(TypedDict):
    """Результат установки цены"""
    success: bool
    nft_id: int
    price_ton: Optional[float]


class GetUserNFTsUseCase:
    """UseCase: Получить NFT пользователя"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NFTRepository(session)
    
    async def execute(
        self,
        user_id: int,
        pagination: PaginationRequest
    ) -> NFTListResponse:
        """Выполнить"""
        items, total = await self.repo.get_user_nfts(user_id, pagination)
        
        return NFTListResponse(
            items=[NFTResponse.model_validate(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
            has_more=(pagination.offset + len(items)) < total
        )


class SetPriceUseCase:
    """UseCase: Установить цену NFT"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NFTRepository(session)
        self.service = NFTService(self.repo)
    
    async def execute(
        self,
        nft_id: int,
        user_id: int,
        price_ton: Optional[float]
    ) -> SetPriceResult:
        """Выполнить"""
        async with get_uow(self.session) as uow:
            nft = await self.service.set_price(nft_id, user_id, price_ton)
            await uow.commit()
            
            return SetPriceResult(
                success=True,
                nft_id=nft.id,
                price_ton=price_ton
            )


class BuyNFTUseCase:
    """UseCase: Купить NFT"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NFTRepository(session)
        self.service = NFTService(self.repo)
    
    async def execute(self, nft_id: int, buyer_id: int):
        """Выполнить покупку"""
        from app.utils.locks import redis_lock
        
        async with redis_lock(f"nft:buy:{nft_id}", timeout=10):
            async with get_uow(self.session) as uow:
                # Логика покупки
                # ...
                await uow.commit()
```

### 5. router.py - HTTP endpoints

```python
"""NFT модуль - Router"""

import logging
from fastapi import APIRouter, Depends

from app.db import AsyncSession, get_db
from app.db.models import User
from app.api.dependencies import get_current_user
from app.shared.pagination import PaginationRequest
from .schemas import (
    NFTListResponse,
    SetPriceRequest,
    BuyRequest,
    NFTResponse
)
from .use_cases import (
    GetUserNFTsUseCase,
    SetPriceUseCase,
    BuyNFTUseCase
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/nft", tags=["NFT"])


@router.post("/my", response_model=NFTListResponse)
async def get_my_nfts(
    pagination: PaginationRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Получить свои NFT"""
    use_case = GetUserNFTsUseCase(session)
    return await use_case.execute(user.id, pagination)


@router.post("/set-price")
async def set_price(
    request: SetPriceRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Установить цену NFT"""
    use_case = SetPriceUseCase(session)
    return await use_case.execute(
        request.nft_id,
        user.id,
        request.price_ton
    )


@router.post("/buy")
async def buy_nft(
    request: BuyRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Купить NFT"""
    use_case = BuyNFTUseCase(session)
    return await use_case.execute(request.nft_id, user.id)
```

### 6. __init__.py - Публичный API модуля

```python
"""NFT модуль"""

from .router import router
from .schemas import NFTResponse, SetPriceRequest, BuyRequest
from .use_cases import GetUserNFTsUseCase, SetPriceUseCase, BuyNFTUseCase


__all__ = [
    "router",
    "NFTResponse",
    "SetPriceRequest",
    "BuyRequest",
    "GetUserNFTsUseCase",
    "SetPriceUseCase",
    "BuyNFTUseCase",
]
```

## 🎯 Преимущества DDD подхода

### 1. Изолированность
- Каждый модуль независим
- Легко понять всю логику модуля
- Можно удалить/заменить модуль целиком

### 2. Масштабируемость
- Легко добавлять новые модули
- Команды могут работать над разными модулями
- Нет конфликтов в одних файлах

### 3. Понятность
- Вся логика NFT в одной папке
- Не нужно прыгать между repositories/, services/, use_cases/
- Новичку легко разобраться

### 4. Тестируемость
- Тесты рядом с модулем
- Легко мокать зависимости
- Изолированное тестирование

## 📁 Итоговая структура

```
backend/project/app/
├── modules/
│   ├── nft/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   ├── use_cases.py
│   │   └── router.py
│   ├── market/
│   ├── trades/
│   ├── offers/
│   ├── presale/
│   ├── channels/
│   ├── auctions/
│   ├── accounts/
│   └── users/
│
├── shared/              # Общий код
│   ├── base_repository.py
│   ├── base_service.py
│   ├── pagination.py
│   └── exceptions.py
│
├── db/                  # БД инфраструктура
│   ├── models/
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── nft.py
│   │   └── ...
│   └── uow.py
│
└── api/
    ├── dependencies.py
    └── main.py
```

## 🚀 Начнем?

Создам структуру для NFT модуля как эталон!
