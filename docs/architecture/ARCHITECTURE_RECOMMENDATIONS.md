# 🏗️ РЕКОМЕНДАЦИИ ПО АРХИТЕКТУРЕ

**Дата:** 6 декабря 2025  
**Цель:** Достижение около идеального состояния бэкенда

---

## ✅ ЧТО УЖЕ ХОРОШО (СОХРАНИТЬ!)

### 1. Clean Architecture
```
Router → UseCase → Service → Repository → Models
```
- ✅ Четкое разделение ответственности
- ✅ Легко тестировать
- ✅ Легко расширять

### 2. Unit of Work Pattern
```python
async with get_uow(session) as uow:
    # Бизнес-логика
    await uow.commit()  # Явный commit
```
- ✅ Автоматический rollback при ошибках
- ✅ Fail-safe: rollback если забыли commit
- ✅ Централизованное управление транзакциями

### 3. Distributed Locks
```python
async with redis_lock(f"offer:accept:{offer_id}", timeout=10):
    # Критическая секция
```
- ✅ Защита от race conditions
- ✅ Работает в распределенной системе
- ✅ Connection pooling для производительности

### 4. Structured Logging
```python
logger.info("Offer accepted", extra={
    "offer_id": offer_id,
    "price": price/1e9,
    "commission": commission/1e9
})
```
- ✅ Loguru вместо logging
- ✅ Контекстная информация
- ✅ JSON формат для Loki

### 5. Type Safety
```python
id: Mapped[int] = mapped_column(primary_key=True)
```
- ✅ SQLAlchemy 2.0 Mapped типы
- ✅ Pydantic схемы
- ✅ Type hints везде

---

## 🔧 ЧТО НУЖНО УЛУЧШИТЬ

### 1. Добавить Retry Механизм

**Проблема:** TON транзакции могут временно падать

**Решение:** Уже есть в `market/use_cases.py`, распространить на все TON операции

```python
from app.utils.retry import retry_async

await retry_async(
    wallet.send_ton,
    max_attempts=3,
    delay=2.0,
    exceptions=(TonError, NetworkError)
)
```

### 2. Добавить Idempotency Keys

**Проблема:** Двойные запросы могут привести к двойным операциям

**Решение:** Уже есть для выводов, добавить для:
- Покупки пресейлов
- Ставок на аукционах
- Принятия офферов

```python
class BuyPresaleRequest(BaseModel):
    presale_id: int
    idempotency_key: str | None = None

# В UseCase:
if request.idempotency_key:
    existing = await self.repo.check_idempotency_key(request.idempotency_key)
    if existing:
        return {"success": True, "idempotent": True}
```

### 3. Добавить Circuit Breaker

**Проблема:** Если TON API падает, все запросы будут висеть

**Решение:** Создать `backend/project/app/utils/circuit_breaker.py`

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
    
    async def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half_open"
            else:
                raise CircuitBreakerOpenError()
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            raise
```

### 4. Добавить Rate Limiting

**Проблема:** Пользователь может спамить запросами

**Решение:** Использовать Redis для rate limiting

```python
from app.utils.rate_limit import rate_limit

@router.post("/buy")
@rate_limit(max_requests=10, window=60)  # 10 запросов в минуту
async def buy_presale(...):
    ...
```

### 5. Добавить Caching

**Проблема:** Некоторые данные запрашиваются часто (фильтры, floor prices)

**Решение:** Redis cache с TTL

```python
from app.utils.cache import cached

@cached(ttl=300)  # 5 минут
async def get_market_filters():
    # Тяжелый запрос к БД
    ...
```

### 6. Добавить Health Checks

**Проблема:** Нет способа проверить здоровье сервиса

**Решение:** Создать endpoint `/health`

```python
@router.get("/health")
async def health_check():
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "ton_api": await check_ton_api()
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={"status": "healthy" if all_healthy else "unhealthy", "checks": checks}
    )
```

### 7. Добавить Metrics

**Проблема:** Нет метрик для мониторинга

**Решение:** Prometheus metrics

```python
from prometheus_client import Counter, Histogram

presale_purchases = Counter('presale_purchases_total', 'Total presale purchases')
presale_purchase_duration = Histogram('presale_purchase_duration_seconds', 'Presale purchase duration')

@presale_purchase_duration.time()
async def buy_presale(...):
    ...
    presale_purchases.inc()
```

### 8. Добавить Request ID

**Проблема:** Сложно отследить запрос через все логи

**Решение:** Middleware для Request ID

```python
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    with logger.contextualize(request_id=request_id):
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

### 9. Добавить Database Connection Pooling

**Проблема:** Может быть недостаточно соединений под нагрузкой

**Решение:** Настроить pool в `database.py`

```python
engine = create_async_engine(
    settings.database,
    pool_size=20,  # Базовый размер пула
    max_overflow=10,  # Дополнительные соединения
    pool_pre_ping=True,  # Проверка соединений
    pool_recycle=3600,  # Пересоздание каждый час
    echo=False
)
```

### 10. Добавить Background Task Manager

**Проблема:** Фоновые задачи запускаются хаотично

**Решение:** Централизованный менеджер

```python
class BackgroundTaskManager:
    def __init__(self):
        self.tasks = {}
    
    def register(self, name: str, func: Callable, interval: int):
        self.tasks[name] = {
            "func": func,
            "interval": interval,
            "task": None
        }
    
    async def start_all(self):
        for name, task_info in self.tasks.items():
            task_info["task"] = asyncio.create_task(
                safe_background_task(
                    task_name=name,
                    task_func=task_info["func"],
                    restart_delay=task_info["interval"]
                )
            )
    
    async def stop_all(self):
        for task_info in self.tasks.values():
            if task_info["task"]:
                task_info["task"].cancel()

# В run.py:
task_manager = BackgroundTaskManager()
task_manager.register("check_transactions", wallet.check_transactions, 5)
task_manager.register("cleanup_old_offers", cleanup_old_offers, 3600)
task_manager.register("process_expired_auctions", process_expired_auctions, 60)

@app.on_event("startup")
async def startup():
    await task_manager.start_all()

@app.on_event("shutdown")
async def shutdown():
    await task_manager.stop_all()
```

---

## 📊 ПРОИЗВОДИТЕЛЬНОСТЬ

### 1. Индексы БД (уже есть, проверить покрытие)

```python
# Проверить что есть индексы на:
- NFT.user_id
- NFT.price (для фильтрации)
- NFTOffer.nft_id
- NFTOffer.user_id
- NFTOffer.updated (для очистки)
- Auction.expired_at
- Auction.user_id
- BalanceWithdraw.idempotency_key (unique)
```

### 2. Eager Loading

```python
# ПЛОХО: N+1 запросов
offers = await session.execute(select(NFTOffer))
for offer in offers:
    print(offer.nft.gift.title)  # Каждый раз новый запрос

# ХОРОШО: 1 запрос
offers = await session.execute(
    select(NFTOffer)
    .options(
        joinedload(NFTOffer.nft).joinedload(NFT.gift)
    )
)
```

### 3. Pagination

```python
# Всегда использовать limit/offset
.offset(page * page_size).limit(page_size)
```

### 4. Bulk Operations

```python
# ПЛОХО: N запросов
for bid in old_bids:
    await session.delete(bid)

# ХОРОШО: 1 запрос
await session.execute(
    delete(AuctionBid).where(AuctionBid.auction_id == auction_id)
)
```

---

## 🔒 БЕЗОПАСНОСТЬ

### 1. Input Validation (уже есть через Pydantic)

```python
class BuyPresaleRequest(BaseModel):
    presale_id: int = Field(gt=0)
    idempotency_key: str | None = Field(max_length=255)
```

### 2. SQL Injection Protection (уже есть через SQLAlchemy)

```python
# ХОРОШО: Параметризованные запросы
.where(User.id == user_id)
```

### 3. Rate Limiting (добавить)

### 4. Authentication (уже есть)

```python
user: User = Depends(get_current_user)
```

### 5. Authorization (добавить проверки)

```python
# Проверять что пользователь владелец
if presale.user_id != user.id:
    raise NotOwnerError()
```

---

## 🧪 ТЕСТИРОВАНИЕ

### 1. Unit Tests

```python
# backend/tests/unit/test_presale_use_cases.py
async def test_buy_presale_insufficient_balance():
    # Arrange
    user = create_user(balance=100)
    presale = create_presale(price=200)
    
    # Act & Assert
    with pytest.raises(InsufficientBalanceError):
        await BuyPresaleUseCase(session).execute(presale.id, user.id)
```

### 2. Integration Tests

```python
# backend/tests/integration/test_presale_api.py
async def test_buy_presale_endpoint(client, auth_headers):
    response = await client.get(
        "/presale/buy?presale_id=1",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
```

### 3. E2E Tests

```python
# backend/tests/e2e/test_presale_flow.py
async def test_full_presale_flow():
    # 1. Создать пресейл
    # 2. Установить цену
    # 3. Купить пресейл
    # 4. Проверить баланс
    ...
```

---

## 📈 МОНИТОРИНГ

### 1. Grafana Dashboards

- Requests per second
- Response time (p50, p95, p99)
- Error rate
- Database connections
- Redis connections
- Background task status

### 2. Loki для логов

- Структурированные JSON логи
- Фильтрация по уровню
- Поиск по request_id

### 3. Alerting

- Error rate > 5%
- Response time > 1s
- Database connections > 80%
- Background task failures

---

## 🚀 DEPLOYMENT

### 1. Blue-Green Deployment

```yaml
# docker-compose.blue.yml
services:
  app-blue:
    environment:
      - enable_telegram_init=false  # Не инициализировать сессии
```

### 2. Health Checks

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### 3. Graceful Shutdown

```python
@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down...")
    await task_manager.stop_all()
    await engine.dispose()
    logger.info("Shutdown complete")
```

---

## 📋 ПРИОРИТЕТЫ

### Неделя 1 (КРИТИЧНО):
1. ✅ Исправить 6 критических проблем
2. ✅ Добавить тесты для критических флоу
3. ✅ Настроить логирование

### Неделя 2 (ВАЖНО):
1. Добавить Health Checks
2. Добавить Metrics
3. Настроить мониторинг
4. Добавить Rate Limiting

### Неделя 3 (УЛУЧШЕНИЯ):
1. Добавить Circuit Breaker
2. Добавить Caching
3. Оптимизировать запросы
4. Добавить E2E тесты

### Неделя 4 (ПОЛИРОВКА):
1. Документация API
2. Performance testing
3. Security audit
4. Code review

---

## 🎯 ИТОГОВАЯ АРХИТЕКТУРА

```
┌─────────────────────────────────────────────────────────┐
│                     Load Balancer                        │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
│   App Instance │  │   App Instance │  │   App Instance │
│   (Stateless)  │  │   (Stateless)  │  │   (Stateless)  │
└───────┬────────┘  └───────┬────────┘  └───────┬────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
│   PostgreSQL   │  │   Redis        │  │   TON API      │
│   (Primary)    │  │   (Sentinel)   │  │                │
└────────────────┘  └────────────────┘  └────────────────┘
        │
┌───────▼────────┐
│   PostgreSQL   │
│   (Replica)    │
└────────────────┘
```

**Характеристики:**
- ✅ Stateless приложение (можно масштабировать горизонтально)
- ✅ Distributed locks через Redis
- ✅ Connection pooling для БД и Redis
- ✅ Health checks для автоматического восстановления
- ✅ Graceful shutdown для zero-downtime deployment
- ✅ Structured logging для отладки
- ✅ Metrics для мониторинга

---

## ✅ РЕЗУЛЬТАТ

После всех улучшений получим:

1. **Надежность:** 99.9% uptime
2. **Производительность:** <100ms response time
3. **Масштабируемость:** Горизонтальное масштабирование
4. **Безопасность:** Защита от всех основных угроз
5. **Наблюдаемость:** Полный мониторинг и логирование
6. **Поддерживаемость:** Чистая архитектура, тесты, документация

**Оценка:** 95%+ готовности к продакшну

---

*Документ создан 6 декабря 2025*
