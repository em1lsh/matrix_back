# 🏗️ Обзор архитектуры Backend

**Дата:** 6 декабря 2025  
**Версия:** 2.0 (новый бэкенд)

---

## 📐 Архитектурный стиль

**Clean Architecture** с разделением на слои:

```
┌─────────────────────────────────────────────────────┐
│                    Presentation                      │
│                  (FastAPI Routers)                   │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                  Application Layer                   │
│                    (Use Cases)                       │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                   Domain Layer                       │
│              (Services, Entities)                    │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│               Infrastructure Layer                   │
│            (Repositories, Database)                  │
└─────────────────────────────────────────────────────┘
```

---

## 📂 Структура проекта

```
backend/project/app/
├── modules/                    # Бизнес-модули
│   ├── presale/               # Предпродажи
│   │   ├── router.py          # FastAPI endpoints
│   │   ├── use_cases.py       # Бизнес-логика
│   │   ├── service.py         # Доменные сервисы
│   │   ├── repository.py      # Работа с БД
│   │   ├── schemas.py         # Pydantic модели
│   │   └── exceptions.py      # Доменные исключения
│   │
│   ├── auctions/              # Аукционы
│   ├── offers/                # Офферы
│   ├── market/                # Маркет
│   └── nft/                   # NFT
│
├── db/                        # База данных
│   ├── models.py              # SQLAlchemy модели
│   ├── uow.py                 # Unit of Work
│   └── base.py                # Базовые классы
│
├── utils/                     # Утилиты
│   ├── logger.py              # Loguru конфигурация
│   ├── locks.py               # Distributed locks
│   ├── retry.py               # Retry механизм
│   └── background_tasks.py    # Фоновые задачи
│
├── shared/                    # Общие компоненты
│   └── exceptions.py          # Базовые исключения
│
└── configs.py                 # Конфигурация
```

---

## 🔄 Поток запроса

### Пример: Покупка пресейла

```python
# 1. Router (Presentation Layer)
@router.get("/buy")
async def buy_presale(presale_id: int, user: User = Depends(get_current_user)):
    return await BuyPresaleUseCase(session).execute(presale_id, user.id)

# 2. UseCase (Application Layer)
class BuyPresaleUseCase:
    async def execute(self, presale_id: int, user_id: int):
        async with redis_lock(f"presale:buy:{presale_id}"):  # Distributed lock
            async with get_uow(self.session) as uow:         # Unit of Work
                # Получение данных через Repository
                presale = await self.repo.get_by_id(presale_id)
                buyer = await self.repo.get_user(user_id)
                
                # Валидация через Service
                self.service.validate_can_buy(presale, buyer)
                
                # Бизнес-логика
                buyer.market_balance -= presale.price
                presale.buyer_id = user_id
                
                await uow.commit()  # Явный commit
                return {"success": True}

# 3. Service (Domain Layer)
class PresaleService:
    def validate_can_buy(self, presale, buyer):
        if presale.price is None:
            raise PresaleNotForSaleError()
        if buyer.market_balance < presale.price:
            raise InsufficientBalanceError()

# 4. Repository (Infrastructure Layer)
class PresaleRepository:
    async def get_by_id(self, id: int) -> NFTPreSale:
        result = await self.session.execute(
            select(NFTPreSale).where(NFTPreSale.id == id)
        )
        return result.scalar_one_or_none()
```

---

## 🎯 Ключевые паттерны

### 1. Unit of Work (UoW)
**Зачем:** Управление транзакциями

```python
async with get_uow(session) as uow:
    # Все изменения в одной транзакции
    user.balance -= 100
    nft.user_id = user.id
    await uow.commit()  # Явный commit
    # Автоматический rollback при ошибке
```

### 2. Repository
**Зачем:** Инкапсуляция работы с БД

```python
class PresaleRepository(BaseRepository[NFTPreSale]):
    async def search(self, filter) -> list[NFTPreSale]:
        # Вся логика запросов здесь
        ...
```

### 3. UseCase
**Зачем:** Бизнес-логика отдельно от роутеров

```python
class BuyPresaleUseCase:
    async def execute(self, presale_id: int, user_id: int):
        # Вся бизнес-логика здесь
        ...
```

### 4. Distributed Locks
**Зачем:** Защита от race conditions

```python
async with redis_lock(f"presale:buy:{presale_id}", timeout=10):
    # Только один процесс может быть здесь
    ...
```

### 5. Domain Exceptions
**Зачем:** Понятные ошибки вместо HTTPException

```python
# ПЛОХО
raise HTTPException(status_code=400, detail="Insufficient balance")

# ХОРОШО
raise InsufficientBalanceError(required=1000, available=500)
```

---

## 🔒 Безопасность

### 1. Distributed Locks (Redis)
- Предотвращение race conditions
- Работает в распределенной системе
- Connection pooling для производительности

### 2. Unit of Work
- Автоматический rollback при ошибках
- Fail-safe: rollback если забыли commit
- Атомарность операций

### 3. Idempotency Keys
- Защита от двойных операций
- Используется для выводов средств

### 4. Input Validation
- Pydantic схемы для всех входных данных
- Type hints везде

---

## 📊 База данных

### SQLAlchemy 2.0
```python
# Mapped типы для type safety
id: Mapped[int] = mapped_column(primary_key=True)
price: Mapped[int] = mapped_column(BigInteger, nullable=False)
```

### Индексы
```python
__table_args__ = (
    Index("ix_auctions_expired_at", "expired_at"),
    Index("ix_auctions_user_expired", "user_id", "expired_at"),
)
```

### Constraints
```python
CheckConstraint("price > 0", name="check_price_positive")
```

---

## 📝 Логирование

### Loguru
```python
from app.utils.logger import get_logger

logger = get_logger(__name__)

logger.info("Presale bought", extra={
    "presale_id": presale_id,
    "user_id": user_id,
    "price": price/1e9
})
```

### Уровни:
- **DEBUG:** Детальная отладка (locks, queries)
- **INFO:** Общая информация (операции, события)
- **WARNING:** Предупреждения (fallback режимы)
- **ERROR:** Ошибки (exceptions)
- **CRITICAL:** Критические ошибки (требуют внимания)

---

## 🚀 Производительность

### 1. Connection Pooling
- PostgreSQL: pool_size=20, max_overflow=10
- Redis: max_connections=100

### 2. Индексы БД
- На всех полях для фильтрации
- Composite индексы для сложных запросов

### 3. Eager Loading
```python
.options(joinedload(NFTOffer.nft).joinedload(NFT.gift))
```

### 4. Pagination
```python
.offset(page * page_size).limit(page_size)
```

---

## 🔄 Фоновые задачи

### Safe Background Tasks
```python
asyncio.create_task(
    safe_background_task(
        task_name="check_transactions",
        task_func=wallet._run_check_transactions,
        restart_delay=30,
        max_consecutive_failures=5
    )
)
```

**Особенности:**
- Автоматический перезапуск при ошибках
- Логирование всех ошибок
- Graceful shutdown

---

## 📚 Дополнительно

- **[ARCHITECTURE_RECOMMENDATIONS.md](ARCHITECTURE_RECOMMENDATIONS.md)** - Рекомендации по улучшению
- **[../database/UOW_USAGE.md](../database/UOW_USAGE.md)** - Использование Unit of Work
- **[../api/USE_CASE_EXAMPLE.md](../api/USE_CASE_EXAMPLE.md)** - Примеры UseCase

---

*Документ обновлён 6 декабря 2025*
