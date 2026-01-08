# Сравнение ref_tests с другими тестами

## Обзор тестов в проекте

В проекте есть несколько типов тестов, каждый со своей целью:

| Тип теста | Файл | Количество | Цель |
|-----------|------|------------|------|
| **Рефакторинг-тесты** | `ref_tests/*.py` | 60 | Проверка работоспособности всех эндпоинтов |
| **Тяжелые эндпоинты** | `test_heavy_endpoints.py` | 26 | Детальное тестирование сложных эндпоинтов |
| **Модели** | `test_models_*.py` | ~50 | Тестирование моделей БД |
| **Безопасность** | `test_security.py` | ~10 | Тестирование безопасности |
| **Интеграционные** | `test_*_integration.py` | ~15 | Интеграция с внешними сервисами |
| **Load тесты** | `load/*.py` | - | Нагрузочное тестирование |

## Детальное сравнение

### 1. ref_tests vs test_heavy_endpoints.py

#### ref_tests (Рефакторинг-тесты)
```python
# Цель: Проверить что эндпоинт работает (200)
@pytest.mark.asyncio
async def test_get_salings_200(self, client: AsyncClient, test_token):
    """POST /api/market/ - список товаров"""
    response = await client.post(
        "/api/market/",
        params={"token": test_token},
        json={"titles": [], "models": [], ...}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
```

**Характеристики:**
- ✅ Быстрые (минимум данных)
- ✅ Простые (один кейс = один тест)
- ✅ Покрывают ВСЕ эндпоинты
- ❌ Не проверяют детальную логику

#### test_heavy_endpoints.py (Тяжелые эндпоинты)
```python
# Цель: Детально проверить бизнес-логику
@pytest.mark.asyncio
async def test_get_salings_with_filters(self, client, test_user, test_token, db_session):
    """POST /api/market/ - фильтрация по коллекциям"""
    # Создаем 25 NFT с разными параметрами
    for i in range(25):
        gift = models.Gift(...)
        nft = models.NFT(...)
        db_session.add(gift)
        db_session.add(nft)
    await db_session.commit()
    
    # Тестируем фильтрацию
    response = await client.post("/api/market/", ...)
    assert len(data) > 0
    assert all(item["gift"]["title"] == "Test Collection" for item in data)
    
    # Тестируем пагинацию
    response_page0 = await client.post("/api/market/", ...)
    response_page1 = await client.post("/api/market/", ...)
    assert page0_ids.isdisjoint(page1_ids)
```

**Характеристики:**
- ✅ Детальная проверка логики
- ✅ Проверка edge cases
- ✅ Проверка пагинации, фильтрации
- ❌ Медленные (много данных)
- ❌ Покрывают только тяжелые эндпоинты

### Когда использовать что?

| Ситуация | ref_tests | test_heavy_endpoints.py |
|----------|-----------|-------------------------|
| Рефакторинг API | ✅ | ❌ |
| Быстрая проверка | ✅ | ❌ |
| Детальное тестирование | ❌ | ✅ |
| CI/CD (быстрый feedback) | ✅ | ❌ |
| Перед релизом | ✅ | ✅ |

---

### 2. ref_tests vs test_models_*.py

#### ref_tests
```python
# Тестируем API эндпоинт
async def test_get_my_nfts_200(self, client, test_token):
    response = await client.get("/api/nft/my", params={"token": test_token})
    assert response.status_code == 200
```

#### test_models_*.py
```python
# Тестируем модель БД
async def test_nft_model_creation(db_session):
    nft = models.NFT(gift_id=1, user_id=1, msg_id=123)
    db_session.add(nft)
    await db_session.commit()
    
    assert nft.id is not None
    assert nft.created_at is not None
```

**Различия:**
- ref_tests → API уровень (HTTP)
- test_models → БД уровень (ORM)

---

### 3. ref_tests vs test_security.py

#### ref_tests
```python
# Проверяем что эндпоинт работает с валидным токеном
async def test_get_salings_200(self, client, test_token):
    response = await client.post("/api/market/", params={"token": test_token}, ...)
    assert response.status_code == 200
```

#### test_security.py
```python
# Проверяем безопасность
async def test_unauthorized_access(client):
    response = await client.post("/api/market/", params={"token": "invalid"}, ...)
    assert response.status_code == 401

async def test_sql_injection(client, test_token):
    response = await client.post("/api/market/", 
        params={"token": test_token},
        json={"titles": ["'; DROP TABLE users; --"]}
    )
    assert response.status_code == 200  # Не должно упасть
```

**Различия:**
- ref_tests → Проверка работоспособности
- test_security → Проверка безопасности

---

### 4. ref_tests vs load тесты

#### ref_tests
```python
# Один запрос
async def test_get_salings_200(self, client, test_token):
    response = await client.post("/api/market/", ...)
    assert response.status_code == 200
```

#### load/locustfile.py
```python
# Множество запросов
class MarketUser(HttpUser):
    @task
    def get_salings(self):
        self.client.post("/api/market/", ...)
    
    # Запускается 100+ пользователей одновременно
```

**Различия:**
- ref_tests → Функциональность
- load тесты → Производительность

---

## Матрица покрытия

### Эндпоинты покрытые разными тестами

| Эндпоинт | ref_tests | test_heavy_endpoints | test_security | load |
|----------|-----------|---------------------|---------------|------|
| POST /api/market/ | ✅ | ✅ | ✅ | ✅ |
| GET /api/market/collections | ✅ | ✅ | ❌ | ✅ |
| GET /api/market/topup-balance | ✅ | ✅ | ❌ | ❌ |
| GET /api/market/output | ❌ | ✅ | ❌ | ❌ |
| POST /api/auctions/ | ✅ | ✅ | ❌ | ✅ |
| POST /api/auctions/new | ✅ | ✅ | ❌ | ❌ |
| GET /api/channels | ✅ | ✅ | ❌ | ✅ |
| GET /api/channels/buy | ✅ | ✅ | ❌ | ❌ |
| GET /api/nft/my | ✅ | ❌ | ❌ | ❌ |
| GET /api/users/me | ✅ | ❌ | ✅ | ❌ |

**Выводы:**
- ref_tests покрывают ВСЕ эндпоинты базовыми тестами
- test_heavy_endpoints покрывают только критичные эндпоинты детально
- test_security покрывают только эндпоинты с авторизацией
- load тесты покрывают только публичные эндпоинты

---

## Рекомендации по использованию

### Ежедневная разработка
```bash
# Быстрая проверка после изменений
pytest backend/tests/ref_tests/ -x --tb=short
```

### Перед коммитом
```bash
# Проверка затронутых эндпоинтов
pytest backend/tests/ref_tests/test_ref_market.py -v
```

### Перед merge request
```bash
# Все рефакторинг-тесты + тяжелые эндпоинты
pytest backend/tests/ref_tests/ -v
pytest backend/tests/test_heavy_endpoints.py -v
```

### Перед релизом
```bash
# Все тесты
pytest backend/tests/ -v

# Load тесты
cd backend/tests/load
locust -f locustfile.py
```

---

## Пирамида тестирования в проекте

```
                    /\
                   /  \
                  / E2E \          ← load тесты (производительность)
                 /______\
                /        \
               / Integration \     ← test_*_integration.py
              /______________\
             /                \
            /   API Tests      \   ← ref_tests + test_heavy_endpoints
           /____________________\
          /                      \
         /     Unit Tests         \ ← test_models_*.py
        /__________________________\
```

**ref_tests находятся на уровне API Tests:**
- Быстрые
- Покрывают все эндпоинты
- Проверяют базовую функциональность
- Запускаются часто

---

## Миграция с test_heavy_endpoints на ref_tests

### Что делать с существующими тестами?

**НЕ удаляйте test_heavy_endpoints.py!**

Эти тесты дополняют ref_tests:
- ref_tests → Быстрая проверка работоспособности
- test_heavy_endpoints → Детальная проверка логики

### Стратегия использования

1. **Разработка нового эндпоинта:**
   ```bash
   # 1. Написать код
   # 2. Добавить тест в ref_tests
   pytest backend/tests/ref_tests/test_ref_market.py::TestRefMarket::test_new_endpoint_200 -v
   # 3. Если эндпоинт сложный - добавить детальный тест в test_heavy_endpoints.py
   ```

2. **Рефакторинг существующего эндпоинта:**
   ```bash
   # 1. Запустить ref_test ДО рефакторинга
   pytest backend/tests/ref_tests/test_ref_market.py::TestRefMarket::test_get_salings_200 -v
   # 2. Провести рефакторинг
   # 3. Запустить ref_test ПОСЛЕ рефакторинга
   pytest backend/tests/ref_tests/test_ref_market.py::TestRefMarket::test_get_salings_200 -v
   # 4. Запустить детальный тест
   pytest backend/tests/test_heavy_endpoints.py::TestMarketEndpoints::test_get_salings_with_filters -v
   ```

3. **Быстрая проверка всех эндпоинтов:**
   ```bash
   # Используйте ref_tests
   pytest backend/tests/ref_tests/ -v
   ```

4. **Детальная проверка перед релизом:**
   ```bash
   # Используйте оба
   pytest backend/tests/ref_tests/ -v
   pytest backend/tests/test_heavy_endpoints.py -v
   ```

---

## Заключение

### ref_tests - это:
- ✅ Быстрые smoke тесты для всех эндпоинтов
- ✅ Инструмент для отслеживания состояния API при рефакторинге
- ✅ Первая линия защиты от регрессий
- ✅ Дополнение к существующим тестам, а не замена

### Используйте ref_tests когда:
- Нужна быстрая проверка работоспособности
- Проводите рефакторинг
- Хотите убедиться что все эндпоинты возвращают 200
- Нужен быстрый feedback в CI/CD

### Используйте test_heavy_endpoints когда:
- Нужна детальная проверка бизнес-логики
- Тестируете сложные сценарии
- Проверяете edge cases
- Готовитесь к релизу

### Используйте оба:
- В CI/CD pipeline (ref_tests быстро, heavy медленно)
- Перед релизом (полная проверка)
- При разработке новых фич (ref для базы, heavy для деталей)
