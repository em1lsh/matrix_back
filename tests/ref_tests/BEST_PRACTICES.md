# Best Practices для рефакторинг-тестов

## Общие принципы

### 1. Один тест = один эндпоинт = один успешный кейс
```python
@pytest.mark.asyncio
async def test_get_salings_200(self, client: AsyncClient, test_token):
    """POST /api/market/ - список товаров"""
    response = await client.post("/api/market/", ...)
    assert response.status_code == 200
```

### 2. Используйте уникальные ID для тестовых данных
```python
def generate_unique_id(prefix: int = 900000000) -> int:
    return prefix + secrets.randbelow(99999999)

# В тесте
gift_id = generate_unique_id()
account_id = f"test_acc_{secrets.token_hex(4)}"
```

### 3. Проверяйте минимум - статус и структуру ответа
```python
# ✅ Хорошо
assert response.status_code == 200
data = response.json()
assert isinstance(data, list)
assert "id" in data[0]

# ❌ Плохо (слишком детально)
assert response.status_code == 200
data = response.json()
assert len(data) == 10
assert data[0]["id"] == 123
assert data[0]["title"] == "Exact Title"
assert data[0]["price"] == 1000000000
```

### 4. Тестируйте ошибки только для критичных кейсов
```python
# ✅ Хорошо - проверяем важную бизнес-логику
async def test_buy_nft_insufficient_balance(self, ...):
    response = await client.get("/api/nft/buy", ...)
    assert response.status_code == 400
    assert "Insufficient balance" in response.json()["detail"]

# ❌ Плохо - не нужно тестировать все возможные ошибки
async def test_buy_nft_invalid_id(self, ...):
    # Это уже покрывается другими тестами
```

## Структура теста

### Шаблон теста
```python
@pytest.mark.asyncio
async def test_endpoint_name_200(
    self,
    client: AsyncClient,
    test_user,
    test_token,
    db_session
):
    """HTTP_METHOD /api/path - краткое описание"""
    
    # 1. Подготовка данных (если нужно)
    gift = models.Gift(id=generate_unique_id(), ...)
    db_session.add(gift)
    await db_session.commit()
    
    # 2. Вызов эндпоинта
    response = await client.get(
        "/api/endpoint",
        params={"token": test_token}
    )
    
    # 3. Проверка результата
    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data
```

## Naming conventions

### Имена тестов
```python
# Формат: test_{endpoint_name}_{expected_status}
test_get_salings_200          # ✅ Успешный кейс
test_buy_nft_insufficient_balance  # ✅ Ошибка с описанием
test_delete_account_200       # ✅ Успешное удаление

# ❌ Плохие имена
test_market_1
test_nft_buy
test_error
```

### Docstrings
```python
# ✅ Хорошо
"""POST /api/market/ - список товаров"""

# ❌ Плохо
"""Тест для получения списка товаров на маркете с фильтрацией"""
```

## Работа с данными

### Создание тестовых данных
```python
# ✅ Хорошо - уникальные ID
gift_id = generate_unique_id()
account_id = f"test_acc_{secrets.token_hex(4)}"

# ❌ Плохо - фиксированные ID (могут конфликтовать)
gift_id = 123456
account_id = "test_account"
```

### Очистка данных
```python
# ✅ Хорошо - данные удаляются автоматически через db_session
# Не нужно явно удалять данные в конце теста

# ❌ Плохо - явная очистка
await db_session.delete(gift)
await db_session.commit()
```

## Fixtures

### Используйте существующие fixtures
```python
# Доступные fixtures из conftest.py:
# - client: AsyncClient
# - test_user: models.User
# - test_token: str
# - db_session: AsyncSession

@pytest.mark.asyncio
async def test_example(
    self,
    client: AsyncClient,      # HTTP клиент
    test_user,                 # Тестовый пользователь
    test_token,                # Токен авторизации
    db_session                 # Сессия БД
):
    ...
```

## Группировка тестов

### Используйте классы для группировки
```python
class TestRefMarket:
    """Тесты для /api/market/* - 9 эндпоинтов"""
    
    @pytest.mark.asyncio
    async def test_get_salings_200(self, ...):
        ...
    
    @pytest.mark.asyncio
    async def test_get_collections_200(self, ...):
        ...
```

## Обработка ошибок

### Когда тестировать ошибки
```python
# ✅ Тестируем критичные бизнес-ошибки
async def test_buy_nft_insufficient_balance(self, ...):
    # Важная проверка баланса
    assert response.status_code == 400
    assert "Insufficient balance" in response.json()["detail"]

# ✅ Тестируем ошибки доступа
async def test_delete_account_not_found(self, ...):
    # Проверка что нельзя удалить чужой аккаунт
    assert response.status_code == 400

# ❌ Не тестируем валидацию входных данных
# Это покрывается Pydantic схемами
```

## Примеры

### Простой GET эндпоинт
```python
@pytest.mark.asyncio
async def test_get_my_nfts_200(self, client: AsyncClient, test_token):
    """GET /api/nft/my - свои NFT"""
    response = await client.get("/api/nft/my", params={"token": test_token})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
```

### POST эндпоинт с телом запроса
```python
@pytest.mark.asyncio
async def test_get_salings_200(self, client: AsyncClient, test_token):
    """POST /api/market/ - список товаров"""
    response = await client.post(
        "/api/market/",
        params={"token": test_token},
        json={
            "titles": [],
            "models": [],
            "patterns": [],
            "backdrops": [],
            "num": None,
            "sort": "price/desc",
            "page": 0,
            "count": 20
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
```

### Эндпоинт с созданием данных
```python
@pytest.mark.asyncio
async def test_new_auction_200(self, client: AsyncClient, test_user, test_token, db_session):
    """POST /api/auctions/new - создание аукциона"""
    # Создаем NFT
    gift_id = generate_unique_id()
    gift = models.Gift(
        id=gift_id,
        title="Auction Test Gift",
        num=1,
        availability_total=1
    )
    db_session.add(gift)
    
    nft = models.NFT(
        gift_id=gift_id,
        user_id=test_user.id,
        msg_id=generate_unique_id(),
        price=None
    )
    db_session.add(nft)
    await db_session.commit()
    
    # Вызываем эндпоинт
    response = await client.post(
        "/api/auctions/new",
        params={"token": test_token},
        json={
            "nft_id": nft.id,
            "start_bid_ton": 5.0,
            "term_hours": 24
        }
    )
    
    # Проверяем результат
    assert response.status_code == 200
    data = response.json()
    assert data["created"] is True
```

## Что НЕ делать

### ❌ Не тестируйте детали реализации
```python
# ❌ Плохо
assert len(data) == 10
assert data[0]["price"] == 1000000000
assert data[0]["user_id"] == test_user.id

# ✅ Хорошо
assert isinstance(data, list)
assert "price" in data[0] if data else True
```

### ❌ Не создавайте сложные зависимости между тестами
```python
# ❌ Плохо
class TestRefMarket:
    auction_id = None
    
    async def test_create_auction(self, ...):
        self.auction_id = ...
    
    async def test_delete_auction(self, ...):
        # Зависит от предыдущего теста!
        await client.delete(f"/api/auctions/{self.auction_id}")

# ✅ Хорошо - каждый тест независим
class TestRefMarket:
    async def test_delete_auction(self, ...):
        # Создаем свои данные
        auction = models.Auction(...)
        db_session.add(auction)
        await db_session.commit()
        
        await client.delete(f"/api/auctions/{auction.id}")
```

### ❌ Не тестируйте внешние сервисы
```python
# ❌ Плохо - требует реального Telegram
async def test_send_gift_to_telegram(self, ...):
    response = await client.get("/api/accounts/send-gifts", ...)
    # Этот тест будет падать без реального Telegram

# ✅ Хорошо - мокаем или пропускаем
@pytest.mark.skip("Requires real Telegram account")
async def test_send_gift_to_telegram(self, ...):
    ...
```

## Запуск и отладка

### Запуск конкретного теста
```bash
# Один тест
pytest backend/tests/ref_tests/test_ref_market.py::TestRefMarket::test_get_salings_200 -v

# Один класс
pytest backend/tests/ref_tests/test_ref_market.py::TestRefMarket -v

# Один файл
pytest backend/tests/ref_tests/test_ref_market.py -v
```

### Отладка падающих тестов
```bash
# Подробный вывод
pytest backend/tests/ref_tests/ -v --tb=long

# Остановка на первой ошибке
pytest backend/tests/ref_tests/ -x

# Вывод print statements
pytest backend/tests/ref_tests/ -s
```

## Checklist для нового теста

- [ ] Имя теста в формате `test_{endpoint}_{status}`
- [ ] Docstring с HTTP методом и путем
- [ ] Используются уникальные ID для данных
- [ ] Проверяется статус код
- [ ] Проверяется базовая структура ответа
- [ ] Тест независим от других тестов
- [ ] Тест не требует внешних сервисов
- [ ] Тест проходит локально
