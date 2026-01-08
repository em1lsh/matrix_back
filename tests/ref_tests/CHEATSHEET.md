# Шпаргалка по ref_tests

## 🚀 Быстрые команды

```bash
# Все тесты
pytest backend/tests/ref_tests/ -v

# Быстрая проверка (остановка на первой ошибке)
pytest backend/tests/ref_tests/ -x --tb=short

# Конкретный модуль
pytest backend/tests/ref_tests/test_ref_market.py -v

# Конкретный тест
pytest backend/tests/ref_tests/test_ref_market.py::TestRefMarket::test_get_salings_200 -v

# Только упавшие тесты
pytest backend/tests/ref_tests/ --lf -v

# С покрытием
pytest backend/tests/ref_tests/ --cov=app/api/routers --cov-report=html

# Параллельно (быстрее)
pytest backend/tests/ref_tests/ -n auto
```

## 📁 Структура файлов

| Файл | Эндпоинты | Тестов |
|------|-----------|--------|
| test_ref_users.py | /api/users/* | 4 |
| test_ref_accounts.py | /api/accounts/* | 3 |
| test_ref_market.py | /api/market/* | 9 |
| test_ref_nft.py | /api/nft/* | 7 |
| test_ref_auctions.py | /api/auctions/* | 6 |
| test_ref_channels.py | /api/channels/* | 8 |
| test_ref_offers.py | /api/offers/* | 5 |
| test_ref_presale.py | /api/presales/* | 5 |
| test_ref_trades.py | /api/trade/* | 13 |

## 📝 Шаблон теста

```python
@pytest.mark.asyncio
async def test_endpoint_name_200(
    self,
    client: AsyncClient,
    test_token,
    test_user,
    db_session
):
    """HTTP_METHOD /api/path - описание"""
    
    # 1. Подготовка (если нужно)
    gift = models.Gift(id=generate_unique_id(), ...)
    db_session.add(gift)
    await db_session.commit()
    
    # 2. Вызов
    response = await client.get(
        "/api/endpoint",
        params={"token": test_token}
    )
    
    # 3. Проверка
    assert response.status_code == 200
    data = response.json()
    assert "field" in data
```

## 🔧 Полезные функции

```python
# Уникальный ID
def generate_unique_id(prefix: int = 900000000) -> int:
    return prefix + secrets.randbelow(99999999)

# Уникальная строка
account_id = f"test_{secrets.token_hex(4)}"

# Старая дата (для тестов с временем)
old_date = datetime.now() - timedelta(days=2)
```

## ✅ Что проверять

```python
# ✅ Статус код
assert response.status_code == 200

# ✅ Тип данных
assert isinstance(data, list)
assert isinstance(data, dict)

# ✅ Наличие полей
assert "id" in data
assert "price" in data

# ✅ Базовая логика
assert data["created"] is True
assert data["deleted"] is True
```

## ❌ Что НЕ проверять

```python
# ❌ Точные значения
assert data["price"] == 1000000000

# ❌ Количество элементов
assert len(data) == 10

# ❌ Детали реализации
assert data[0]["user"]["balance"] == test_user.balance
```

## 🎯 Naming conventions

```python
# Имена тестов
test_get_salings_200              # ✅ Успешный кейс
test_buy_nft_insufficient_balance # ✅ Ошибка с описанием
test_delete_account_200           # ✅ Успешное удаление

# Docstrings
"""POST /api/market/ - список товаров"""  # ✅
```

## 🔄 Workflow рефакторинга

```bash
# 1. ДО
pytest backend/tests/ref_tests/test_ref_market.py -v
# ✅ Все зеленое

# 2. Рефакторинг
# ... меняем код ...

# 3. ПОСЛЕ
pytest backend/tests/ref_tests/test_ref_market.py -v
# ✅ Все зеленое → успех
# ❌ Ошибки → исправить
```

## 🐛 Отладка

```bash
# Подробный вывод
pytest backend/tests/ref_tests/ -vv --tb=long

# С print statements
pytest backend/tests/ref_tests/ -s

# С отладчиком
pytest backend/tests/ref_tests/ --pdb

# Профилирование
pytest backend/tests/ref_tests/ --durations=10
```

## 📊 Fixtures

```python
# Доступные fixtures
client: AsyncClient      # HTTP клиент
test_user: models.User   # Тестовый пользователь
test_token: str          # Токен авторизации
db_session: AsyncSession # Сессия БД
```

## 🎨 Примеры

### GET эндпоинт
```python
@pytest.mark.asyncio
async def test_get_my_nfts_200(self, client, test_token):
    response = await client.get("/api/nft/my", params={"token": test_token})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### POST эндпоинт
```python
@pytest.mark.asyncio
async def test_get_salings_200(self, client, test_token):
    response = await client.post(
        "/api/market/",
        params={"token": test_token},
        json={"titles": [], "page": 0, "count": 20}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### DELETE эндпоинт
```python
@pytest.mark.asyncio
async def test_delete_account_200(self, client, test_user, test_token, db_session):
    account = models.Account(id="test_acc", user_id=test_user.id, ...)
    db_session.add(account)
    await db_session.commit()
    
    response = await client.delete(
        "/api/accounts",
        params={"account_id": "test_acc", "token": test_token}
    )
    assert response.status_code == 200
    assert response.json()["deleted"] is True
```

### Тест на ошибку
```python
@pytest.mark.asyncio
async def test_buy_nft_insufficient_balance(self, client, test_token):
    response = await client.get(
        "/api/nft/buy",
        params={"nft_id": 999999, "token": test_token}
    )
    assert response.status_code == 400
    assert "Insufficient balance" in response.json()["detail"]
```

## 📚 Документация

- [README.md](README.md) - Основная документация
- [COVERAGE.md](COVERAGE.md) - Покрытие эндпоинтов
- [BEST_PRACTICES.md](BEST_PRACTICES.md) - Лучшие практики
- [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) - Примеры использования
- [COMPARISON.md](COMPARISON.md) - Сравнение с другими тестами

## 🔗 Полезные ссылки

```bash
# Запуск скриптов
./backend/tests/run_ref_tests.sh  # Linux/Mac
backend\tests\run_ref_tests.bat   # Windows

# Документация pytest
https://docs.pytest.org/

# Документация httpx
https://www.python-httpx.org/
```

## 💡 Советы

1. **Используйте уникальные ID** для избежания конфликтов
2. **Проверяйте минимум** - только статус и структуру
3. **Не создавайте зависимости** между тестами
4. **Запускайте часто** - тесты быстрые (~30 сек)
5. **Обновляйте COVERAGE.md** при добавлении тестов

## 🎯 Когда использовать

| Ситуация | Команда |
|----------|---------|
| Быстрая проверка | `pytest backend/tests/ref_tests/ -x` |
| Рефакторинг | `pytest backend/tests/ref_tests/test_ref_market.py -v` |
| Перед коммитом | `pytest backend/tests/ref_tests/ -v` |
| Отладка | `pytest backend/tests/ref_tests/ -vv --tb=long` |
| CI/CD | `pytest backend/tests/ref_tests/ -v --tb=short` |

## 📈 Статистика

- Всего тестов: **60**
- Покрытие: **100%** эндпоинтов
- Время выполнения: **~30 секунд**
- Файлов: **9**

---

**Быстрый старт**: `pytest backend/tests/ref_tests/ -v`
