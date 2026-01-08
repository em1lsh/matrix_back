# UoW Load Testing Guide

## Цель

Проверить производительность и надежность после внедрения Unit of Work и distributed locks.

## Что тестируем

1. **Производительность** - не ухудшилась ли скорость работы
2. **Race conditions** - защищены ли критичные операции
3. **Стабильность** - нет ли deadlocks под нагрузкой
4. **Масштабируемость** - как система ведет себя при росте нагрузки

---

## Быстрый старт

### 1. Запустить приложение

```bash
cd backend
poetry run uvicorn project.app.main:app --reload --port 8000
```

### 2. Запустить Redis (если еще не запущен)

```bash
docker-compose up -d redis
```

### 3. Запустить быстрый тест (1 минута)

```bash
cd backend/tests/load
quick_uow_test.bat
```

Откроется отчет в браузере автоматически.

---

## Полное тестирование

### Запуск всех тестов (10, 50, 100 пользователей)

```bash
cd backend/tests/load
run_uow_load_test.bat
```

Время выполнения: ~8 минут

---

## Ручной запуск

### Запуск Locust Web UI

```bash
cd backend
poetry run locust -f tests/load/locustfile_uow.py --host=http://localhost:8000
```

Откройте браузер: http://localhost:8089

Настройки:
- Number of users: 20
- Spawn rate: 5
- Host: http://localhost:8000

Нажмите "Start swarming"

---

## Интерпретация результатов

### Метрики

**Response Time (ms):**
- Median: < 100ms ✅
- 95th percentile: < 500ms ✅
- 99th percentile: < 1000ms ✅

**Requests per Second (RPS):**
- 10 users: 50-100 RPS ✅
- 50 users: 200-400 RPS ✅
- 100 users: 300-600 RPS ✅

**Failure Rate:**
- < 1% ✅ (отлично)
- 1-5% ⚠️ (приемлемо)
- > 5% ❌ (проблема)

### Что проверять

1. **Нет race conditions**
   - При одновременной покупке NFT только один успешно купит
   - Балансы пользователей корректны
   - Нет двойных продаж

2. **Нет deadlocks**
   - Все запросы завершаются
   - Нет зависших транзакций
   - Response time стабильный

3. **Производительность**
   - Response time не сильно вырос (допустимо +10-20%)
   - RPS не сильно упал (допустимо -10-20%)
   - Система стабильна под нагрузкой

---

## Сценарии тестирования

### Сценарий 1: Обычная нагрузка
```bash
poetry run locust -f tests/load/locustfile_uow.py \
    --headless \
    --users=20 \
    --spawn-rate=5 \
    --run-time=2m \
    --host=http://localhost:8000
```

### Сценарий 2: Стресс-тест race conditions
```bash
poetry run locust -f tests/load/locustfile_uow.py \
    --headless \
    --users=50 \
    --spawn-rate=50 \
    --run-time=1m \
    --host=http://localhost:8000 \
    --user-classes=StressTestUser
```

Все 50 пользователей одновременно пытаются купить ОДИН NFT.
Ожидается: только один успешно купит, остальные получат ошибку.

---

## Troubleshooting

### Проблема: High failure rate

**Причины:**
- Приложение не запущено
- Redis не доступен
- База данных перегружена

**Решение:**
1. Проверить что приложение работает: `curl http://localhost:8000/docs`
2. Проверить Redis: `docker ps | grep redis`
3. Проверить логи приложения

### Проблема: Slow response time

**Причины:**
- Много одновременных запросов
- Distributed locks создают очередь
- База данных медленная

**Решение:**
1. Уменьшить количество пользователей
2. Увеличить spawn rate (медленнее добавлять пользователей)
3. Оптимизировать запросы к БД

### Проблема: Deadlocks

**Признаки:**
- Запросы зависают
- Response time растет
- Timeout errors

**Решение:**
1. Проверить логи на deadlocks
2. Уменьшить timeout для locks
3. Проверить порядок блокировок

---

## Результаты

### Ожидаемые улучшения после UoW

**Надежность:**
- ✅ Нет race conditions (было: возможны)
- ✅ Нет двойных продаж (было: возможны)
- ✅ Автоматический rollback (было: ручной)

**Производительность:**
- ⚠️ Response time: +10-20% (из-за locks)
- ⚠️ RPS: -10-20% (из-за locks)
- ✅ Стабильность: значительно лучше

**Вывод:** Небольшое снижение производительности оправдано значительным повышением надежности.

---

## Следующие шаги

1. ✅ Запустить baseline тесты
2. ✅ Проверить что нет race conditions
3. ✅ Проверить что нет deadlocks
4. ⏳ Оптимизировать медленные запросы
5. ⏳ Настроить мониторинг в production

---

**Дата:** 3 декабря 2024  
**Статус:** Готово к тестированию
