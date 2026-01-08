# ✅ DDD Architecture - Реализовано

**Дата:** 6 декабря 2025  
**Статус:** NFT модуль готов как эталон

---

## 🎯 Что реализовано

### 1. Структура DDD (Вертикальные слайсы)

```
backend/project/app/
├── modules/                    # Bounded Contexts
│   └── nft/                   # ✅ NFT модуль (эталон)
│       ├── __init__.py        # Публичный API
│       ├── schemas.py         # Pydantic схемы
│       ├── repository.py      # Работа с БД
│       ├── service.py         # Бизнес-логика
│       ├── use_cases.py       # Оркестрация
│       └── router.py          # HTTP endpoints
│
├── shared/                    # ✅ Общие компоненты
│   ├── __init__.py
│   └── base_repository.py    # Базовый репозиторий
│
├── api/schemas/base.py        # ✅ Базовые схемы (Pagination, etc.)
├── db/                        # Существующая БД инфраструктура
└── exceptions/                # Существующие исключения
```

### 2. NFT модуль - Полная реализация

#### schemas.py (8 схем)
- ✅ `NFTResponse` - ответ NFT
- ✅ `SetPriceRequest` - установка цены
- ✅ `BuyRequest` - покупка
- ✅ `ReturnRequest` - возврат
- ✅ `NFTDealsFilter` - фильтр сделок
- ✅ `NFTDealResponse` - сделка
- ✅ `NFTListResponse` - список с пагинацией

#### repository.py (9 методов)
- ✅ `get_with_gift()` - NFT с подарком
- ✅ `get_with_relations()` - NFT со всеми связями
- ✅ `get_user_nfts()` - NFT пользователя с пагинацией
- ✅ `get_for_purchase()` - NFT для покупки (с блокировкой)
- ✅ `get_user_sells()` - продажи пользователя
- ✅ `get_user_buys()` - покупки пользователя
- ✅ `get_gift_deals()` - сделки по подарку
- ✅ + базовые CRUD из `BaseRepository`

#### service.py (5 методов)
- ✅ `validate_ownership()` - проверка владения
- ✅ `validate_available()` - проверка доступности
- ✅ `validate_balance()` - проверка баланса
- ✅ `calculate_commission()` - расчет комиссии
- ✅ `set_price()` - установка цены

#### use_cases.py (6 use cases)
- ✅ `GetUserNFTsUseCase` - получить NFT пользователя
- ✅ `SetPriceUseCase` - установить цену
- ✅ `BuyNFTUseCase` - купить NFT
- ✅ `GetUserSellsUseCase` - получить продажи
- ✅ `GetUserBuysUseCase` - получить покупки
- ✅ `GetGiftDealsUseCase` - получить сделки по подарку

#### router.py (6 endpoints)
- ✅ `POST /nft/my` - список своих NFT
- ✅ `POST /nft/set-price` - установить цену
- ✅ `POST /nft/buy` - купить NFT
- ✅ `GET /nft/sells` - история продаж
- ✅ `GET /nft/buys` - история покупок
- ✅ `POST /nft/deals` - сделки по подарку

---

## 🏗️ Архитектурные решения

### 1. Разделение ответственности

```python
# Router - только HTTP
@router.post("/buy")
async def buy_nft(request: BuyRequest, ...):
    use_case = BuyNFTUseCase(session)
    return await use_case.execute(request.nft_id, user.id)

# UseCase - оркестрация
class BuyNFTUseCase:
    async def execute(self, nft_id, buyer_id):
        async with redis_lock(...):
            async with get_uow(...):
                # Координация операций
                nft = await self.repo.get_for_purchase(nft_id)
                self.service.validate_balance(buyer, nft)
                # ...

# Service - бизнес-логика
class NFTService:
    def validate_balance(self, buyer, nft):
        if buyer.market_balance < nft.price:
            raise InsufficientBalanceError(...)

# Repository - работа с БД
class NFTRepository:
    async def get_for_purchase(self, nft_id):
        return await self.session.execute(
            select(NFT).where(...).with_for_update()
        )
```

### 2. Использование UoW и Locks

```python
# В BuyNFTUseCase
async with redis_lock(f"nft:buy:{nft_id}", timeout=10):
    async with get_uow(self.session) as uow:
        # Все операции в транзакции
        nft = await self.repo.get_for_purchase(nft_id)
        # ... бизнес-логика
        await uow.commit()  # Атомарный commit
```

### 3. Пагинация

```python
# В Repository
async def get_user_nfts(self, user_id, pagination):
    # Count
    total = await self.session.scalar(count_query)
    
    # Data
    query = select(NFT).offset(pagination.offset).limit(pagination.limit)
    items = await self.session.execute(query)
    
    return items, total

# В UseCase
return NFTListResponse(
    items=[...],
    total=total,
    limit=pagination.limit,
    offset=pagination.offset,
    has_more=(pagination.offset + len(items)) < total
)
```

### 4. Валидация на всех уровнях

```python
# Pydantic (schemas.py)
class SetPriceRequest(BaseModel):
    price_ton: float | None = Field(None, ge=0, le=100000)
    
    @field_validator("price_ton")
    @classmethod
    def validate_price(cls, v):
        if v and v < 0.1:
            raise ValueError("Минимум 0.1 TON")
        return round(v, 2) if v else None

# Service (service.py)
def validate_ownership(self, nft, user_id):
    if nft.user_id != user_id:
        raise PermissionDeniedError("NFT", nft.id)

# Repository (repository.py)
async def get_for_purchase(self, nft_id):
    # SELECT FOR UPDATE для блокировки
    return await self.session.execute(
        select(NFT).where(...).with_for_update()
    )
```

---

## 📊 Преимущества реализации

### 1. Изолированность модулей
- Вся логика NFT в одной папке `modules/nft/`
- Легко найти и понять код
- Можно удалить/заменить модуль целиком

### 2. Тестируемость
```python
# Легко мокать зависимости
def test_set_price():
    mock_repo = Mock(NFTRepository)
    service = NFTService(mock_repo)
    
    result = await service.set_price(1, 1, 100.0)
    assert result.price == 100000000000
```

### 3. Переиспользование
```python
# Один сервис в разных use cases
class SetPriceUseCase:
    def __init__(self, session):
        self.service = NFTService(NFTRepository(session))

class BuyNFTUseCase:
    def __init__(self, session):
        self.service = NFTService(NFTRepository(session))  # Тот же
```

### 4. Масштабируемость
- Легко добавлять новые модули
- Команды работают над разными модулями
- Нет конфликтов в файлах

---

## 🚀 Следующие шаги

### Создать остальные модули по эталону NFT:

1. **market/** (приоритет 1)
   - Поиск NFT на маркете
   - Фильтры (collections, models, patterns, backdrops)
   - Графики цен
   - Вывод средств

2. **trades/** (приоритет 2)
   - CRUD трейдов
   - Предложения на трейды
   - Принятие/отклонение

3. **offers/** (приоритет 3)
   - CRUD офферов
   - Принятие/отклонение

4. **presale/** (приоритет 4)
   - CRUD предпродаж
   - Покупка предпродаж

5. **channels/** (приоритет 5)
   - CRUD каналов
   - Покупка каналов

6. **auctions/** (приоритет 6)
   - CRUD аукционов
   - Ставки на аукционы

7. **accounts/** (приоритет 7)
   - CRUD аккаунтов
   - Авторизация аккаунтов

8. **users/** (приоритет 8)
   - Профиль пользователя
   - История операций

---

## 📝 Шаблон для новых модулей

### 1. Создать структуру
```bash
mkdir app/modules/имя_модуля
touch app/modules/имя_модуля/__init__.py
touch app/modules/имя_модуля/schemas.py
touch app/modules/имя_модуля/repository.py
touch app/modules/имя_модуля/service.py
touch app/modules/имя_модуля/use_cases.py
touch app/modules/имя_модуля/router.py
```

### 2. Скопировать из NFT и адаптировать
- `schemas.py` - заменить модели
- `repository.py` - адаптировать запросы
- `service.py` - адаптировать валидацию
- `use_cases.py` - адаптировать оркестрацию
- `router.py` - адаптировать endpoints

### 3. Зарегистрировать роутер
```python
# app/api/main.py
from app.modules.имя_модуля import router as имя_router

app.include_router(имя_router)
```

---

## ✅ Итоги

**NFT модуль готов как эталон!**

- ✅ Полная типизация и валидация
- ✅ DDD архитектура (вертикальные слайсы)
- ✅ Repository → Service → UseCase → Router
- ✅ UoW для транзакций
- ✅ Distributed locks для race conditions
- ✅ Пагинация
- ✅ Логирование
- ✅ Кастомные исключения
- ✅ Документация endpoints

**Можно копировать структуру для остальных 7 модулей!** 🚀
