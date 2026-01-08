# PostgreSQL vs MySQL - Сравнение производительности

## Конфигурация тестов

### Общие параметры
- **Пользователи**: 50 concurrent
- **Spawn Rate**: 5 users/sec
- **Данные**: 1,000 users, 100 gifts, 500 NFTs, 100 accounts

### MySQL (Stage 2)
- **База данных**: MySQL 8
- **Драйвер**: aiomysql
- **Длительность**: 10 минут
- **Host**: localhost:8001

### PostgreSQL (Текущий тест)
- **База данных**: PostgreSQL 16
- **Драйвер**: asyncpg
- **Длительность**: 5 минут
- **Host**: 127.0.0.1:8001

---

## Общие результаты

| Метрика | MySQL | PostgreSQL | Изменение |
|---------|-------|------------|-----------|
| **Total Requests** | 14,588 | 7,358 | -49.6% (меньше времени) |
| **Success Rate** | 93.7% | 80.6% | **-13.1%** ⚠️ |
| **Failed Requests** | 922 (6.3%) | 1,428 (19.4%) | **+13.1%** ⚠️ |
| **RPS** | 24.32 | 24.59 | **+1.1%** ✅ |
| **Avg Response Time** | 36.67ms | 6.76ms | **-81.6%** ✅✅✅ |
| **Median Response** | 51ms | 6ms | **-88.2%** ✅✅✅ |
| **95th Percentile** | 62ms | 9ms | **-85.5%** ✅✅✅ |
| **99th Percentile** | 69ms | 13ms | **-81.2%** ✅✅✅ |
| **Max Response** | 257ms | 212ms | **-17.5%** ✅ |

---

## Детальное сравнение по эндпоинтам

### 1. POST /market/ (list items) - Главный эндпоинт

| Метрика | MySQL | PostgreSQL | Улучшение |
|---------|-------|------------|-----------|
| Requests | 9,064 | 1,324 | - |
| Success Rate | 100% | 92.1% | **-7.9%** ⚠️ |
| Avg Response | 55ms | 7ms | **-87.3%** ✅✅✅ |
| Median | - | 6ms | - |
| 95th Percentile | - | 9ms | - |
| 99th Percentile | - | 13ms | - |

**Вывод**: PostgreSQL в **7.8 раз быстрее** на главном эндпоинте! Но есть 7.9% ошибок.

### 2. GET /accounts

| Метрика | MySQL | PostgreSQL | Улучшение |
|---------|-------|------------|-----------|
| Requests | 4,602 | 699 | - |
| Success Rate | 100% | 91.6% | **-8.4%** ⚠️ |
| Avg Response | 7ms | 6.7ms | **-4.3%** ✅ |
| Median | - | 6ms | - |

**Вывод**: Оба быстрые, PostgreSQL немного быстрее, но есть ошибки.

### 3. Новые эндпоинты (только PostgreSQL тест)

PostgreSQL тест покрывает **намного больше эндпоинтов**:
- GET /nft/my, /nft/buys, /nft/sells, /nft/deals
- GET /trade/my, /trade/deals, /trade/proposals
- GET /auctions/my, /auctions/deals
- POST /market/models, /market/patterns, /market/backdrops
- И многие другие

**Средний response time**: 6-8ms для большинства эндпоинтов ✅

---

## Проблемные эндпоинты (100% failure)

### Критические проблемы:

1. **POST /market/floor** - 274 requests, 100% failure
2. **GET /offers/my** - 182 requests, 100% failure  
3. **GET /users/me** - 190 requests, 100% failure
4. **GET /users/balance-topups** - 118 requests, 100% failure
5. **POST /auctions/ (list)** - 79 requests, 100% failure
6. **POST /presale/ (list)** - 73 requests, 100% failure

**Причины**:
- Эндпоинты возвращают ошибки (404/500)
- Не хватает данных в БД
- Проблемы с авторизацией

---

## Ключевые выводы

### ✅ Преимущества PostgreSQL

1. **Драматическое улучшение скорости**
   - Response time в **5-8 раз быстрее** на основных эндпоинтах
   - Median 6ms vs 51ms (в 8.5 раз быстрее!)
   - 99th percentile 13ms vs 69ms (в 5.3 раза быстрее!)

2. **Стабильный RPS**
   - 24.59 RPS vs 24.32 RPS
   - Система справляется с нагрузкой

3. **Драйвер asyncpg**
   - Намного быстрее чем aiomysql
   - Лучшая асинхронная производительность

### ⚠️ Проблемы PostgreSQL теста

1. **Высокий процент ошибок (19.4%)**
   - MySQL: 6.3% (только /health)
   - PostgreSQL: 19.4% (множество эндпоинтов)
   - Причина: больше эндпоинтов в тесте, многие не работают

2. **Проблемные эндпоинты**
   - 6 эндпоинтов с 100% failure rate
   - Нужно исправить или исключить из теста

3. **Неполные данные**
   - Не хватает данных для некоторых эндпоинтов
   - Нужно улучшить seed скрипт

---

## Рекомендации по оптимизации

### Немедленные действия

1. **Исправить проблемные эндпоинты**
   - Проверить логи для /market/floor, /offers/my, /users/me
   - Добавить недостающие данные в seed скрипт
   - Исправить ошибки 404/500

2. **Улучшить seed данные**
   ```python
   # Добавить:
   - nft_orders (для /offers/my)
   - auctions (для /auctions/)
   - presales (для /presale/)
   - balance_topups (для /users/balance-topups)
   ```

3. **Повторить тест с исправлениями**
   - Цель: Success Rate > 95%
   - Сравнить с MySQL на равных условиях

### Дальнейшая оптимизация

1. **Настройка PostgreSQL**
   ```ini
   shared_buffers = 256MB
   effective_cache_size = 1GB
   work_mem = 4MB
   max_connections = 200
   ```

2. **Connection Pool**
   ```python
   pool_size = 20
   max_overflow = 40
   pool_timeout = 30
   ```

3. **Индексы**
   ```sql
   CREATE INDEX idx_nfts_price ON nfts(price);
   CREATE INDEX idx_nfts_user_id ON nfts(user_id);
   CREATE INDEX idx_users_token ON users(token);
   ```

4. **Кеширование**
   - Redis для частых запросов
   - Cache-Control headers
   - Query result caching

---

## Итоговая оценка

### PostgreSQL: **A-** (отличная производительность, но есть проблемы)

**Плюсы**:
- ✅ Response time в 5-8 раз быстрее
- ✅ Стабильный RPS
- ✅ Отличная производительность asyncpg
- ✅ Готов к масштабированию

**Минусы**:
- ⚠️ 19.4% ошибок (vs 6.3% на MySQL)
- ⚠️ Проблемные эндпоинты нужно исправить
- ⚠️ Неполные тестовые данные

### Следующие шаги

1. Исправить проблемные эндпоинты (1-2 часа)
2. Улучшить seed данные (30 минут)
3. Повторить тест (5 минут)
4. Тест на 100 пользователей (5 минут)
5. Тест на 200 пользователей (5 минут)
6. Применить оптимизации (2-3 часа)
7. Финальное тестирование (30 минут)

**Общее время до production-ready**: 4-6 часов

---

## Заключение

**PostgreSQL показывает выдающуюся производительность** - в 5-8 раз быстрее MySQL на ключевых эндпоинтах. Однако нужно исправить проблемные эндпоинты и улучшить тестовые данные для честного сравнения.

После исправлений ожидаем:
- Success Rate > 95%
- Response time стабильно < 10ms
- Готовность к 200+ concurrent users
- Production-ready система

**Рекомендация**: Продолжить с PostgreSQL, исправить проблемы, провести полное тестирование.
