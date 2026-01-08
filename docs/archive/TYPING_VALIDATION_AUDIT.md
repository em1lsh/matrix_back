# Аудит типизации и валидации данных

**Дата проверки:** 6 декабря 2025  
**Проверено:** Backend проект (FastAPI + SQLAlchemy + Pydantic)

---

## 📊 Общая оценка: 7/10

### ✅ Сильные стороны

#### 1. **Pydantic схемы (9/10)**
- ✅ Все API схемы используют Pydantic BaseModel
- ✅ Правильное использование современного синтаксиса типов (`str | None` вместо `Optional[str]`)
- ✅ Использование `typing.Literal` для ограничения значений
- ✅ Хорошая структура с разделением на request/response модели
- ✅ Документация через docstrings

**Примеры хорошей типизации:**
```python
# schemas/user.py
class UserResponose(BaseModel):
    id: int
    language: str = "en"
    payment_status: bool = False
    group: typing.Literal["member", "moderator", "admin", "owner"] = "member"

# schemas/market.py
class SalingFilter(BaseModel):
    sort: typing.Literal[
        "created_at/asc", "created_at/desc",
        "price/asc", "price/desc",
        "num/asc", "num/desc",
        "model_rarity/asc", "model_rarity/desc",
    ] = "price/asc"
```

#### 2. **SQLAlchemy модели (8/10)**
- ✅ Использование `Mapped[]` для типизации колонок
- ✅ Правильные типы для всех полей
- ✅ Nullable поля корректно типизированы (`Mapped[str | None]`)
- ✅ Relationships типизированы с forward references
- ✅ Composite indexes для оптимизации

**Пример:**
```python
class User(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    token: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    market_balance: Mapped[int] = mapped_column(BigInteger, default=0)
    accounts: Mapped[list["Account"]] = relationship("Account", back_populates="user")
```

#### 3. **Use Cases (9/10)**
- ✅ Использование TypedDict для результатов
- ✅ Полная типизация всех методов
- ✅ Правильные return types
- ✅ Типизация параметров

**Пример:**
```python
class BuyNFTResult(TypedDict):
    success: bool
    nft_id: int
    deal_id: int
    buyer_id: int
    seller_id: int
    price: int
    commission: int

async def execute(self, nft_id: int, buyer_id: int) -> BuyNFTResult:
    ...
```

---

## ⚠️ Проблемы и недостатки

### 1. **Отсутствие Pydantic валидаторов (КРИТИЧНО)**

**Проблема:** Нет ни одного кастомного валидатора в схемах

```python
# ❌ Текущее состояние
class NewAuctionRequest(BaseModel):
    nft_id: int
    step_bid: float = 10
    start_bid_ton: float
    term_hours: int = 1

# ✅ Должно быть
from pydantic import BaseModel, Field, field_validator

class NewAuctionRequest(BaseModel):
    nft_id: int = Field(gt=0, description="ID NFT")
    step_bid: float = Field(gt=0, le=1000, description="Шаг ставки")
    start_bid_ton: float = Field(gt=0, le=10000, description="Начальная ставка")
    term_hours: int = Field(ge=1, le=168, description="Срок аукциона (1-168 часов)")
    
    @field_validator('start_bid_ton')
    @classmethod
    def validate_start_bid(cls, v: float) -> float:
        if v < 0.1:
            raise ValueError('Минимальная ставка 0.1 TON')
        return v
```

**Найдено:** 0 валидаторов  
**Ожидается:** 20-30 валидаторов для критичных полей

### 2. **Отсутствие Field() constraints**

**Проблема:** Не используются встроенные ограничения Pydantic

```python
# ❌ Текущее
class SalingFilter(BaseModel):
    page: int = 0
    count: int = 20
    price_min: float | None = 0
    price_max: float | None = 0

# ✅ Должно быть
class SalingFilter(BaseModel):
    page: int = Field(ge=0, description="Номер страницы")
    count: int = Field(ge=1, le=100, description="Количество на странице")
    price_min: float | None = Field(None, ge=0, description="Минимальная цена")
    price_max: float | None = Field(None, ge=0, description="Максимальная цена")
```

### 3. **Использование Any типа**

**Найдено:** 30+ использований `Any` в интеграциях

```python
# ❌ Плохо
async def _get_nfts_impl(self, http_client: Any) -> schemas.MarketNFTs:
    ...

# ✅ Хорошо
from aiohttp import ClientSession

async def _get_nfts_impl(self, http_client: ClientSession) -> schemas.MarketNFTs:
    ...
```

**Рекомендация:** Создать Protocol или TypeAlias для http_client

### 4. **Отсутствие mypy в CI/CD**

**Проблема:** mypy установлен в dev-dependencies, но не используется

```bash
# Проверка показала
$ python -m mypy --version
No module named mypy
```

**Рекомендация:** 
```toml
# pyproject.toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
strict_equality = true

[[tool.mypy.overrides]]
module = "telethon.*"
ignore_missing_imports = true
```

### 5. **Неправильное использование @hybrid_property**

**Найдено в:** `models/user.py` - Gift модель

```python
# ❌ НЕПРАВИЛЬНО
@hybrid_property
def get_telegram_url(self,) -> str:  # Запятая после self!
    return f"https://t.me/nft/{slugify_str(str(self.title))}-{self.num}"

# ✅ ПРАВИЛЬНО - вариант 1 (обычный метод)
def get_telegram_url(self) -> str:
    return f"https://t.me/nft/{slugify_str(str(self.title))}-{self.num}"

# ✅ ПРАВИЛЬНО - вариант 2 (property)
@property
def telegram_url(self) -> str:
    return f"https://t.me/nft/{slugify_str(str(self.title))}-{self.num}"
```

**Проблема:** `@hybrid_property` предназначен для SQL-выражений, не для простых методов

### 6. **Отсутствие валидации на уровне роутеров**

**Проблема:** Нет дополнительной валидации в эндпоинтах

```python
# ❌ Текущее
@market_router.get("/output")
async def output(
    ton_amount: float,
    address: str,
    idempotency_key: str | None = None,
    ...
):
    # Валидация только внутри функции
    required_nanotons = int(ton_amount * 1e9)
    if user.market_balance < required_nanotons:
        raise InsufficientBalanceError(...)

# ✅ Должно быть
from pydantic import BaseModel, Field, validator

class WithdrawRequest(BaseModel):
    ton_amount: float = Field(gt=0, le=10000, description="Сумма вывода")
    address: str = Field(min_length=48, max_length=48, description="TON адрес")
    idempotency_key: str | None = Field(None, min_length=16, max_length=64)
    
    @field_validator('address')
    @classmethod
    def validate_ton_address(cls, v: str) -> str:
        if not v.startswith('EQ') and not v.startswith('UQ'):
            raise ValueError('Неверный формат TON адреса')
        return v

@market_router.post("/output")
async def output(
    request: WithdrawRequest,
    db_session: AsyncSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    ...
```

### 7. **Опечатка в названии класса**

```python
# ❌ schemas/user.py
class UserResponose(BaseModel):  # Опечатка: Respono"s"e
    ...

# ✅ Должно быть
class UserResponse(BaseModel):
    ...
```

### 8. **Отсутствие валидации email и phone**

```python
# ❌ Текущее
class Account(Base):
    phone: Mapped[str | None] = mapped_column(String(32), unique=True)

# ✅ Должно быть в схеме
from pydantic import BaseModel, Field, field_validator
import re

class AccountCreateRequest(BaseModel):
    phone: str = Field(pattern=r'^\+\d{10,15}$')
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r'^\+\d{10,15}$', v):
            raise ValueError('Неверный формат телефона')
        return v
```

---

## 📋 Детальная статистика

### Pydantic схемы
- **Всего схем:** 30+
- **С валидаторами:** 0 ❌
- **С Field constraints:** 0 ❌
- **С Literal типами:** 3 ✅
- **С docstrings:** 15 ✅

### SQLAlchemy модели
- **Всего моделей:** 15+
- **С Mapped типами:** 100% ✅
- **С indexes:** 80% ✅
- **С relationships:** 100% ✅

### API роутеры
- **Всего эндпоинтов:** 50+
- **С типизацией параметров:** 100% ✅
- **С Pydantic моделями:** 70% ⚠️
- **С response_model:** 90% ✅

### Use Cases
- **Всего use cases:** 5+
- **С TypedDict результатами:** 100% ✅
- **С типизацией методов:** 100% ✅

---

## 🎯 Приоритетные рекомендации

### Высокий приоритет (критично)

1. **Добавить Pydantic валидаторы для критичных полей**
   - Финансовые операции (amount, price, balance)
   - ID полей (nft_id, user_id, etc.)
   - Адреса и телефоны
   - Временные диапазоны

2. **Использовать Field() constraints**
   - Минимальные/максимальные значения
   - Длина строк
   - Regex паттерны
   - Описания для документации

3. **Настроить mypy и добавить в CI/CD**
   ```bash
   poetry run mypy project/app --strict
   ```

4. **Исправить @hybrid_property в Gift модели**

5. **Исправить опечатку UserResponose → UserResponse**

### Средний приоритет

6. **Заменить Any на конкретные типы**
   - Создать Protocol для HTTP клиентов
   - Типизировать все интеграции

7. **Добавить валидацию на уровне роутеров**
   - Создать Request модели для всех POST/PUT эндпоинтов
   - Переместить query параметры в Pydantic модели

8. **Добавить Config для Pydantic моделей**
   ```python
   class Config:
       from_attributes = True
       validate_assignment = True
       str_strip_whitespace = True
   ```

### Низкий приоритет

9. **Добавить примеры в схемы**
   ```python
   class Config:
       json_schema_extra = {
           "example": {
               "nft_id": 123,
               "start_bid_ton": 10.5
           }
       }
   ```

10. **Создать базовые классы для общих паттернов**
    ```python
    class PaginationRequest(BaseModel):
        page: int = Field(ge=0, default=0)
        count: int = Field(ge=1, le=100, default=20)
    ```

---

## 📝 Примеры улучшений

### Пример 1: Улучшение схемы аукциона

```python
# БЫЛО
class NewAuctionRequest(BaseModel):
    nft_id: int
    step_bid: float = 10
    start_bid_ton: float
    term_hours: int = 1

# СТАЛО
from pydantic import BaseModel, Field, field_validator

class NewAuctionRequest(BaseModel):
    """Запрос на создание нового аукциона"""
    
    nft_id: int = Field(
        gt=0,
        description="ID NFT для аукциона",
        examples=[123, 456]
    )
    step_bid: float = Field(
        gt=0,
        le=1000,
        default=10,
        description="Шаг ставки в TON"
    )
    start_bid_ton: float = Field(
        gt=0,
        le=10000,
        description="Начальная ставка в TON"
    )
    term_hours: int = Field(
        ge=1,
        le=168,
        default=1,
        description="Срок аукциона в часах (1-168)"
    )
    
    @field_validator('start_bid_ton')
    @classmethod
    def validate_start_bid(cls, v: float) -> float:
        if v < 0.1:
            raise ValueError('Минимальная ставка 0.1 TON')
        if v > 10000:
            raise ValueError('Максимальная ставка 10000 TON')
        return round(v, 2)  # Округление до 2 знаков
    
    @field_validator('step_bid')
    @classmethod
    def validate_step_bid(cls, v: float, info) -> float:
        start_bid = info.data.get('start_bid_ton', 0)
        if v > start_bid:
            raise ValueError('Шаг ставки не может быть больше начальной ставки')
        return round(v, 2)
    
    class Config:
        json_schema_extra = {
            "example": {
                "nft_id": 123,
                "step_bid": 5.0,
                "start_bid_ton": 50.0,
                "term_hours": 24
            }
        }
```

### Пример 2: Улучшение фильтра маркета

```python
# БЫЛО
class SalingFilter(BaseModel):
    page: int = 0
    count: int = 20
    titles: list[str] | None = []
    num: int | None = None
    price_min: float | None = 0
    price_max: float | None = 0

# СТАЛО
from pydantic import BaseModel, Field, field_validator, model_validator

class SalingFilter(BaseModel):
    """Фильтр для поиска NFT на маркете"""
    
    page: int = Field(
        ge=0,
        default=0,
        description="Номер страницы (начиная с 0)"
    )
    count: int = Field(
        ge=1,
        le=100,
        default=20,
        description="Количество элементов на странице"
    )
    titles: list[str] | None = Field(
        None,
        max_length=50,
        description="Фильтр по названиям коллекций"
    )
    models: list[str] | None = Field(
        None,
        max_length=50,
        description="Фильтр по моделям"
    )
    num: int | None = Field(
        None,
        ge=1,
        description="Номер NFT"
    )
    price_min: float | None = Field(
        None,
        ge=0,
        description="Минимальная цена в TON"
    )
    price_max: float | None = Field(
        None,
        ge=0,
        description="Максимальная цена в TON"
    )
    
    @model_validator(mode='after')
    def validate_price_range(self) -> 'SalingFilter':
        if self.price_min and self.price_max:
            if self.price_min > self.price_max:
                raise ValueError('price_min не может быть больше price_max')
        return self
    
    @field_validator('titles', 'models')
    @classmethod
    def validate_list_length(cls, v: list[str] | None) -> list[str] | None:
        if v and len(v) > 50:
            raise ValueError('Максимум 50 элементов в фильтре')
        return v
```

### Пример 3: Типизация HTTP клиента

```python
# БЫЛО
async def _get_nfts_impl(self, http_client: Any) -> schemas.MarketNFTs:
    ...

# СТАЛО
from typing import Protocol
from aiohttp import ClientSession

class HTTPClient(Protocol):
    """Протокол для HTTP клиента"""
    
    async def get(self, url: str, **kwargs) -> Any: ...
    async def post(self, url: str, **kwargs) -> Any: ...
    async def close(self) -> None: ...

async def _get_nfts_impl(
    self,
    http_client: ClientSession | HTTPClient
) -> schemas.MarketNFTs:
    ...
```

---

## 🔧 План внедрения

### Неделя 1: Критичные исправления
- [ ] Исправить @hybrid_property в Gift
- [ ] Исправить опечатку UserResponose
- [ ] Настроить mypy
- [ ] Добавить валидаторы для финансовых операций

### Неделя 2: Валидация схем
- [ ] Добавить Field constraints во все схемы
- [ ] Добавить валидаторы для ID полей
- [ ] Добавить валидацию адресов и телефонов

### Неделя 3: Типизация интеграций
- [ ] Создать Protocol для HTTP клиентов
- [ ] Заменить Any на конкретные типы
- [ ] Добавить типизацию в bot модуль

### Неделя 4: Документация и тесты
- [ ] Добавить примеры в схемы
- [ ] Написать тесты для валидаторов
- [ ] Обновить документацию API

---

## ✅ Заключение

**Текущее состояние:** Хорошая базовая типизация, но отсутствует валидация

**Основные проблемы:**
1. Нет Pydantic валидаторов (0 из 30+ схем)
2. Не используются Field constraints
3. Много Any типов в интеграциях
4. mypy не настроен

**Рекомендации:**
- Начать с добавления валидаторов для критичных операций (финансы, NFT)
- Настроить mypy и добавить в CI/CD
- Постепенно улучшать существующие схемы
- Создать базовые классы для общих паттернов

**Оценка после исправлений:** 9/10 ⭐
