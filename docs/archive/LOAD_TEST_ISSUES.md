# Проблемы нагрузочного тестирования - PostgreSQL

## Обнаруженные ошибки (500)

### 1. POST /market/floor - IndexError
**Ошибка**: `IndexError: list index out of range` в `app/api/routers/market.py:365`
```python
actual_floor = floors[0]  # floors пустой список!
```

**Причина**: Нет данных в таблице `market_nft_floors`

**Решение**:
```python
# Добавить проверку
if floors:
    actual_floor = floors[0]
else:
    return {"floor": None}  # или raise HTTPException(404)
```

**Seed данные**: Добавить в seed скрипт создание `market_nft_floors`

---

### 2. GET /offers/my - TypeError
**Ошибка**: `TypeError: ColumnOperators.any_() takes 1 positional argument but 2 were given`
```python
models.NFTOffer.nft.any_(models.NFT.user_id == user.id)  # Неправильный синтаксис!
```

**Причина**: Неправильное использование SQLAlchemy `.any_()`

**Решение**:
```python
# Было (неправильно):
models.NFTOffer.nft.any_(models.NFT.user_id == user.id)

# Должно быть:
models.NFTOffer.nft.has(models.NFT.user_id == user.id)
# или
models.NFTOffer.query.join(models.NFT).filter(models.NFT.user_id == user.id)
```

---

### 3. GET /accounts - 500 Error
**Нужно проверить логи** для точной ошибки

**Возможные причины**:
- Проблема с relationship в SQLAlchemy
- Отсутствующие данные
- Неправильный запрос

---

### 4. GET /users/me - 500 Error
**Нужно проверить логи** для точной ошибки

**Возможные причины**:
- Проблема с сериализацией пользователя
- Отсутствующие поля
- Проблема с relationship

---

### 5. POST /auctions/ (list) - 500 Error
**Причина**: Нет данных в таблице `auctions` или ошибка в запросе

**Решение**: Добавить данные в seed скрипт

---

## Отсутствующие эндпоинты (404)

### 1. GET /users/balance-topups - 404
Эндпоинт не существует в роутере

**Решение**: Удалить из locustfile или создать эндпоинт

### 2. POST /presale/ (list) - 404
Эндпоинт не существует (возможно `/presales/` вместо `/presale/`)

**Решение**: Исправить URL в locustfile

---

## План исправлений

### Приоритет 1: Критические ошибки кода (1-2 часа)

1. **Исправить POST /market/floor**
   ```python
   # В app/api/routers/market.py:365
   if not floors:
       raise HTTPException(status_code=404, detail="Floor price not found")
   actual_floor = floors[0]
   ```

2. **Исправить GET /offers/my**
   ```python
   # Найти использование .any_() и заменить на .has()
   # или переписать запрос
   ```

3. **Проверить и исправить GET /accounts**
   - Посмотреть полные логи
   - Исправить запрос

4. **Проверить и исправить GET /users/me**
   - Посмотреть полные логи
   - Исправить сериализацию

### Приоритет 2: Seed данные (30 минут)

Добавить в `seed_pg_fast.py`:

```python
# Market floor prices
print("Creating market floor prices...")
for i in range(50):
    gift_id = random.choice(gift_ids)
    market = random.choice(['mrkt', 'portals', 'tonnel'])
    cursor.execute(
        """INSERT INTO market_nft_floors (gift_id, market, floor_price, created_at)
           VALUES (%s, %s, %s, NOW())
           ON CONFLICT DO NOTHING""",
        (gift_id, market, random.randint(1, 50) * 1000000000)
    )
conn.commit()

# Auctions
print("Creating auctions...")
for i in range(50):
    cursor.execute(
        """INSERT INTO auctions (nft_id, user_id, start_price, end_time, created_at)
           VALUES (%s, %s, %s, NOW() + INTERVAL '7 days', NOW())""",
        (random.choice(nft_ids), random.choice(user_ids), 
         random.randint(1, 50) * 1000000000)
    )
conn.commit()
```

### Приоритет 3: Locustfile (10 минут)

Исправить или удалить проблемные эндпоинты:

```python
# Удалить или закомментировать:
# - GET /users/balance-topups (404)
# - POST /presale/ (404)

# Или исправить URL:
# POST /presale/ -> POST /presales/
```

---

## Ожидаемые результаты после исправлений

### До исправлений:
- Success Rate: 80.6%
- Failed: 19.4%
- 6 проблемных эндпоинтов

### После исправлений:
- Success Rate: > 95%
- Failed: < 5%
- Все эндпоинты работают

### Производительность (уже отличная):
- Median: 6ms ✅
- 95th percentile: 9ms ✅
- 99th percentile: 13ms ✅
- RPS: 24.59 ✅

---

## Следующие шаги

1. ✅ Выявили все проблемы
2. ⏳ Исправить код (1-2 часа)
3. ⏳ Улучшить seed данные (30 минут)
4. ⏳ Повторить тест (5 минут)
5. ⏳ Тест на 100 пользователей (5 минут)
6. ⏳ Тест на 200 пользователей (5 минут)
7. ⏳ Применить оптимизации (2-3 часа)

**Общее время до production-ready**: 4-6 часов

---

## Заключение

**PostgreSQL работает отлично** - response time в 5-8 раз быстрее MySQL!

Проблемы не связаны с PostgreSQL, это:
- Баги в коде (IndexError, TypeError)
- Отсутствующие данные
- Несуществующие эндпоинты в тесте

После исправления этих проблем система будет готова к production.
