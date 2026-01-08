# Анализ кастомных исключений и логирования

## Текущее состояние

### 1. Исключения в проекте

#### ✅ Существующие кастомные исключения
Найдено **только 3 кастомных исключения** в `app/account/_exceptions.py`:
```python
class CreateAccountError(Exception): pass
class PasswordRequired(Exception): pass
class TelegramAuthError(Exception): pass
```

#### ❌ Проблемы текущего подхода

**Массовое использование HTTPException напрямую:**
- Найдено **50+ мест** с `raise HTTPException`
- Нет централизованной обработки ошибок
- Дублирование кода обработки ошибок
- Сложно отследить типы ошибок
- Нет структурированного логирования ошибок

**Использование базовых исключений:**
- `raise Exception("...")` - 1 место (channels.py)
- `raise ValueError(...)` - 8 мест (security, schemas, utils)
- `raise RuntimeError(...)` - 3 места (uow, db utils, alembic)

**Примеры проблемного кода:**
```python
# channels.py - строка 439
if channel.price > user.market_balance:
    raise HTTPException(
        status_code=http.HTTPStatus.BAD_REQUEST,
        detail="Insufficient balance."
    )

# channels.py - строка 499
if not result:
    raise Exception("Channel transfer failed")  # ❌ Базовое исключение
```

### 2. Логирование в проекте

#### ✅ Существующая инфраструктура
- Настроен базовый logging через `run.py`
- Есть `LogBufferHandler` для health endpoint
- Используется `TimedRotatingFileHandler`
- Настроены уровни для uvicorn, telethon, urllib3

#### ❌ Проблемы логирования

**Минимальное использование:**
- Логирование используется только в **8 файлах**:
  - `utils/locks.py` - Redis блокировки
  - `utils/retry.py` - повторные попытки
  - `utils/background_tasks.py` - фоновые задачи
  - `wallet/wallet.py` - TON транзакции
  - `db/crud.py` - операции БД
  - `db/uow.py` - Unit of Work
  - `api/routers/channels.py` - один роутер
  - `tests/load/locustfile_uow.py` - нагрузочные тесты

**Отсутствует логирование в критичных местах:**
- ❌ Нет логов в большинстве роутеров (auctions, market, presale, trades, nft, offers)
- ❌ Нет логов при обработке HTTPException
- ❌ Нет структурированного логирования бизнес-операций
- ❌ Нет контекста пользователя в логах
- ❌ Нет трейсинга запросов

**Примеры отсутствия логов:**
```python
# market.py - покупка NFT без логов
@market_router.post('/buy/{nft_id}')
async def buy_nft(...):
    # Критичная операция - нет логов!
    if nft.price > user.market_balance:
        raise HTTPException(...)  # Ошибка не логируется
    
    # Транзакция - нет логов!
    user.market_balance -= nft.price
    nft.user_id = user.id
```

---

## Оценка сложности внедрения

### 🔴 Высокая сложность (7/10)

#### Причины:

1. **Масштаб изменений**
   - 50+ мест с HTTPException нужно рефакторить
   - 15+ роутеров требуют добавления логирования
   - Нужно создать иерархию из 20-30 кастомных исключений

2. **Архитектурные изменения**
   - Нужен exception handler middleware
   - Требуется структурированное логирование
   - Необходим контекст запроса (request_id, user_id)
   - Интеграция с UoW для логирования транзакций

3. **Риски**
   - Изменения затронут весь API слой
   - Нужно тестировать каждый endpoint
   - Возможны breaking changes в error responses
   - Требуется обновление документации API

---

## Предлагаемая архитектура

### 1. Иерархия исключений

```python
# app/exceptions/__init__.py

class AppException(Exception):
    """Базовое исключение приложения"""
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


# Бизнес-логика
class BusinessLogicError(AppException):
    """Ошибки бизнес-логики"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, status_code=400, **kwargs)


class InsufficientBalanceError(BusinessLogicError):
    error_code = "INSUFFICIENT_BALANCE"


class NFTNotFoundError(BusinessLogicError):
    error_code = "NFT_NOT_FOUND"


class ChannelNotFoundError(BusinessLogicError):
    error_code = "CHANNEL_NOT_FOUND"


# Авторизация
class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, status_code=401, error_code="AUTH_FAILED", **kwargs)


class PermissionDeniedError(AppException):
    def __init__(self, message: str = "Permission denied", **kwargs):
        super().__init__(message, status_code=403, error_code="PERMISSION_DENIED", **kwargs)


# Внешние сервисы
class ExternalServiceError(AppException):
    def __init__(self, service: str, message: str, **kwargs):
        super().__init__(
            f"{service}: {message}",
            status_code=502,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service},
            **kwargs
        )


class TelegramAPIError(ExternalServiceError):
    def __init__(self, message: str, **kwargs):
        super().__init__("Telegram", message, **kwargs)


class TONWalletError(ExternalServiceError):
    def __init__(self, message: str, **kwargs):
        super().__init__("TON Wallet", message, **kwargs)


# Блокировки и конкурентность
class LockError(AppException):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, status_code=409, error_code="LOCK_ERROR", **kwargs)


class ResourceLockedError(LockError):
    error_code = "RESOURCE_LOCKED"


# База данных
class DatabaseError(AppException):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, status_code=500, error_code="DATABASE_ERROR", **kwargs)
```

### 2. Exception Handler Middleware

```python
# app/api/exception_handlers.py

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import traceback
from typing import Union

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Обработчик кастомных исключений приложения"""
    
    # Логируем с контекстом
    log_context = {
        "error_code": exc.error_code,
        "status_code": exc.status_code,
        "path": request.url.path,
        "method": request.method,
        "user_id": getattr(request.state, "user_id", None),
        "request_id": getattr(request.state, "request_id", None),
        "details": exc.details,
    }
    
    if exc.status_code >= 500:
        logger.error(
            f"Server error: {exc.message}",
            extra=log_context,
            exc_info=True
        )
    else:
        logger.warning(
            f"Client error: {exc.message}",
            extra=log_context
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Обработчик неожиданных исключений"""
    
    request_id = getattr(request.state, "request_id", "unknown")
    user_id = getattr(request.state, "user_id", None)
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "user_id": user_id,
            "request_id": request_id,
            "exception_type": type(exc).__name__,
        },
        exc_info=True
    )
    
    # В продакшене не показываем детали
    if settings.environment == "production":
        message = "Internal server error"
    else:
        message = str(exc)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": message,
                "request_id": request_id,
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Обработчик ошибок валидации Pydantic"""
    
    logger.warning(
        "Validation error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors(),
            "user_id": getattr(request.state, "user_id", None),
        }
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request data",
                "details": exc.errors(),
            }
        }
    )


# Регистрация в app
def register_exception_handlers(app):
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
```

### 3. Структурированное логирование

```python
# app/utils/logging.py

import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Контекст запроса
request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})


class StructuredLogger:
    """Обертка для структурированного логирования"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log(self, level: int, message: str, **kwargs):
        """Внутренний метод логирования с контекстом"""
        context = request_context.get()
        
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "level": logging.getLevelName(level),
            **context,
            **kwargs
        }
        
        # Логируем как JSON для удобного парсинга
        self.logger.log(level, json.dumps(log_data, ensure_ascii=False))
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, exc_info=False, **kwargs):
        if exc_info:
            import traceback
            kwargs['traceback'] = traceback.format_exc()
        self._log(logging.ERROR, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)


# Middleware для установки контекста
class RequestContextMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            import uuid
            request_id = str(uuid.uuid4())
            
            # Устанавливаем контекст
            context = {
                "request_id": request_id,
                "path": scope["path"],
                "method": scope["method"],
            }
            
            token = request_context.set(context)
            
            try:
                await self.app(scope, receive, send)
            finally:
                request_context.reset(token)
        else:
            await self.app(scope, receive, send)


# Декоратор для логирования операций
def log_operation(operation_name: str):
    """Декоратор для автоматического логирования операций"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            logger = StructuredLogger(func.__module__)
            
            logger.info(
                f"Starting operation: {operation_name}",
                operation=operation_name,
                function=func.__name__,
            )
            
            try:
                result = await func(*args, **kwargs)
                
                logger.info(
                    f"Completed operation: {operation_name}",
                    operation=operation_name,
                    function=func.__name__,
                    status="success",
                )
                
                return result
            
            except Exception as e:
                logger.error(
                    f"Failed operation: {operation_name}",
                    operation=operation_name,
                    function=func.__name__,
                    status="failed",
                    error=str(e),
                    exc_info=True,
                )
                raise
        
        return wrapper
    return decorator
```

### 4. Интеграция с UoW

```python
# app/db/uow.py (дополнения)

class UnitOfWork:
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self._session: Optional[AsyncSession] = None
        self._rolled_back = False
        self.logger = StructuredLogger(__name__)  # ✅ Добавляем логгер
    
    async def __aenter__(self):
        self._session = self.session_factory()
        self.logger.debug("UoW session started")  # ✅ Логируем
        return self
    
    async def commit(self):
        if self._rolled_back:
            raise RuntimeError("Cannot commit after rollback")
        
        try:
            await self._session.commit()
            self.logger.info("UoW committed successfully")  # ✅ Логируем
        except Exception as e:
            self.logger.error(
                "UoW commit failed",
                error=str(e),
                exc_info=True
            )  # ✅ Логируем ошибку
            await self.rollback()
            raise DatabaseError(f"Failed to commit transaction: {e}") from e
    
    async def rollback(self):
        if not self._rolled_back:
            await self._session.rollback()
            self._rolled_back = True
            self.logger.warning("UoW rolled back")  # ✅ Логируем
```

---

## План внедрения

### Этап 1: Инфраструктура (2-3 дня)
- [ ] Создать `app/exceptions/` с иерархией исключений
- [ ] Создать exception handlers
- [ ] Настроить структурированное логирование
- [ ] Добавить middleware для контекста запросов
- [ ] Написать тесты для exception handlers

### Этап 2: Критичные модули (3-4 дня)
- [ ] Рефакторинг `market.py` (покупка/продажа NFT)
- [ ] Рефакторинг `channels.py` (передача каналов)
- [ ] Рефакторинг `auctions.py` (аукционы)
- [ ] Рефакторинг `trades.py` (обмены)
- [ ] Добавить логирование в UoW

### Этап 3: Остальные модули (2-3 дня)
- [ ] Рефакторинг `presale.py`
- [ ] Рефакторинг `nft.py`
- [ ] Рефакторинг `offers.py`
- [ ] Рефакторинг `accounts.py`
- [ ] Рефакторинг `wallet/wallet.py`

### Этап 4: Тестирование (2-3 дня)
- [ ] Обновить существующие тесты
- [ ] Добавить тесты для новых исключений
- [ ] Проверить логирование в тестах
- [ ] Нагрузочное тестирование с логами

### Этап 5: Документация (1 день)
- [ ] Обновить API документацию
- [ ] Документировать коды ошибок
- [ ] Создать гайд по логированию
- [ ] Обновить README

**Общее время: 10-14 дней**

---

## Примеры рефакторинга

### До:
```python
# market.py
@market_router.post('/buy/{nft_id}')
async def buy_nft(
    nft_id: int,
    db_session: AsyncSession = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    nft = await db_session.get(models.NFT, nft_id)
    
    if nft is None:
        raise HTTPException(
            status_code=http.HTTPStatus.BAD_REQUEST,
            detail="NFT does not exists."
        )
    
    if nft.price > user.market_balance:
        raise HTTPException(
            status_code=http.HTTPStatus.BAD_REQUEST,
            detail="Insufficient balance."
        )
    
    user.market_balance -= nft.price
    nft.user_id = user.id
    
    await db_session.commit()
    
    return {"status": "ok"}
```

### После:
```python
# market.py
from app.exceptions import NFTNotFoundError, InsufficientBalanceError
from app.utils.logging import StructuredLogger, log_operation

logger = StructuredLogger(__name__)

@market_router.post('/buy/{nft_id}')
@log_operation("buy_nft")  # ✅ Автоматическое логирование
async def buy_nft(
    nft_id: int,
    uow: UnitOfWork = Depends(get_uow),  # ✅ Используем UoW
    user: models.User = Depends(get_current_user)
):
    async with uow:
        # Получаем NFT
        nft = await uow.session.get(models.NFT, nft_id)
        
        if nft is None:
            logger.warning(
                "NFT not found",
                nft_id=nft_id,
                user_id=user.id
            )
            raise NFTNotFoundError(f"NFT {nft_id} not found")  # ✅ Кастомное исключение
        
        # Проверяем баланс
        if nft.price > user.market_balance:
            logger.warning(
                "Insufficient balance for NFT purchase",
                nft_id=nft_id,
                user_id=user.id,
                required=nft.price,
                available=user.market_balance
            )
            raise InsufficientBalanceError(
                f"Required {nft.price}, available {user.market_balance}"
            )  # ✅ Кастомное исключение
        
        # Выполняем покупку
        logger.info(
            "Processing NFT purchase",
            nft_id=nft_id,
            user_id=user.id,
            price=nft.price
        )
        
        user.market_balance -= nft.price
        nft.user_id = user.id
        
        await uow.commit()  # ✅ Логирование внутри UoW
        
        logger.info(
            "NFT purchased successfully",
            nft_id=nft_id,
            user_id=user.id,
            new_balance=user.market_balance
        )
        
        return {"status": "ok", "nft_id": nft_id}
```

---

## Метрики для отслеживания

После внедрения можно отслеживать:

1. **Ошибки по типам**
   - Количество каждого типа исключений
   - Топ-5 самых частых ошибок
   - Тренды по времени

2. **Производительность**
   - Время выполнения операций
   - Медленные запросы
   - Bottleneck'и

3. **Бизнес-метрики**
   - Неудачные покупки (причины)
   - Проблемы с балансом
   - Ошибки внешних сервисов

4. **Качество кода**
   - Покрытие логированием
   - Количество необработанных исключений
   - Время отклика на ошибки

---

## Выводы

### 🔴 Критичность: ВЫСОКАЯ

**Текущие риски:**
- Сложно отлаживать проблемы в продакшене
- Нет visibility в бизнес-операции
- Дублирование кода обработки ошибок
- Невозможно собирать метрики по ошибкам

**Польза от внедрения:**
- ✅ Централизованная обработка ошибок
- ✅ Структурированные логи для анализа
- ✅ Лучшая отладка и мониторинг
- ✅ Понятные коды ошибок для фронтенда
- ✅ Метрики и аналитика

**Рекомендация:**
Внедрять поэтапно, начиная с критичных модулей (market, channels, auctions).
Не откладывать - чем больше кода, тем сложнее рефакторинг.
