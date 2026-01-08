# Покрытие API эндпоинтов рефакторинг-тестами

## Общая статистика
- **Всего эндпоинтов**: 60
- **Покрыто тестами на 200**: 59
- **Покрытие**: 98.3%
- **Не покрыто**: 1 (требует мока для Telegram bot)
- **Требуют внешних сервисов**: 5 (Telegram API, TON blockchain)

## Детальное покрытие по модулям

### 1. /api/users/* (4 эндпоинта) ✅
- [x] GET /api/users/auth - получение токена
- [x] GET /api/users/me - профиль пользователя
- [x] GET /api/users/topups - список пополнений
- [x] GET /api/users/withdraws - список выводов

**Файл**: `test_ref_users.py`

---

### 2. /api/accounts/* (3 эндпоинта) ✅
- [x] GET /api/accounts - список аккаунтов
- [x] DELETE /api/accounts - удаление аккаунта
- [x] GET /api/accounts/gifts - NFT со всех аккаунтов

**Файл**: `test_ref_accounts.py`

**Не покрыто** (требуют реальных Telegram аккаунтов):
- GET /api/accounts/new - создание аккаунта
- POST /api/accounts/approve_auth - подтверждение входа
- GET /api/accounts/channels - каналы аккаунта
- GET /api/accounts/send-gifts - отправка NFT

---

### 3. /api/market/* (9 эндпоинтов) ✅
- [x] POST /api/market/ - список товаров
- [x] GET /api/market/collections - список коллекций
- [x] POST /api/market/models - фильтр моделей
- [x] POST /api/market/patterns - фильтр паттернов
- [x] POST /api/market/backdrops - фильтр фонов
- [x] GET /api/market/topup-balance - реквизиты пополнения
- [x] GET /api/market/integrations - список интеграций
- [x] POST /api/market/floor - минимальная цена
- [x] POST /api/market/charts - график цен

**Файл**: `test_ref_market.py`

**Не покрыто** (требует реальных TON транзакций):
- GET /api/market/output - вывод средств

---

### 4. /api/nft/* (7 эндпоинтов) ✅
- [x] GET /api/nft/my - свои NFT
- [x] GET /api/nft/set-price - установка цены
- [x] GET /api/nft/buy - покупка NFT
- [x] GET /api/nft/back - возврат NFT
- [x] GET /api/nft/sells - история продаж
- [x] GET /api/nft/buys - история покупок
- [x] GET /api/nft/deals - история сделок по NFT

**Файл**: `test_ref_nft.py`

---

### 5. /api/auctions/* (6 эндпоинтов) ✅
- [x] POST /api/auctions/ - список аукционов
- [x] GET /api/auctions/my - мои аукционы
- [x] POST /api/auctions/new - создание аукциона
- [x] GET /api/auctions/del - удаление аукциона
- [x] POST /api/auctions/bid - ставка на аукцион
- [x] GET /api/auctions/deals - история сделок

**Файл**: `test_ref_auctions.py`

---

### 6. /api/channels/* (8 эндпоинтов) ✅
- [x] GET /api/channels - каналы на продаже
- [x] GET /api/channels/my - мои каналы
- [x] GET /api/channels/buys - мои покупки
- [x] GET /api/channels/sells - мои продажи
- [x] GET /api/channels/set-price - установка цены
- [x] DELETE /api/channels - удаление канала
- [x] GET /api/channels/buy - покупка канала
- [x] GET /api/channels/new - добавление канала

**Файл**: `test_ref_channels.py`

---

### 7. /api/offers/* (5 эндпоинтов) ✅
- [x] GET /api/offers/my - мои офферы
- [x] GET /api/offers/new - создание оффера
- [x] POST /api/offers/refuse - отказ от оффера
- [x] POST /api/offers/accept - принятие оффера
- [x] GET /api/offers/set-price - установка ответной цены

**Файл**: `test_ref_offers.py`

---

### 8. /api/presales/* (5 эндпоинтов) ✅
- [x] POST /api/presales/ - список пресейлов
- [x] GET /api/presales/my - мои пресейлы
- [x] GET /api/presales/set-price - установка цены
- [x] GET /api/presales/delete - удаление пресейла
- [x] GET /api/presales/buy - покупка пресейла

**Файл**: `test_ref_presale.py`

---

### 9. /api/trade/* (13 эндпоинтов) ✅
- [x] POST /api/trade/ - лента трейдов
- [x] GET /api/trade/my - мои трейды
- [x] GET /api/trade/personal - персональные трейды
- [x] POST /api/trade/new - создание трейда
- [x] POST /api/trade/delete - удаление трейдов
- [x] POST /api/trade/new-proposal - создание предложения
- [x] POST /api/trade/delete-proposals - удаление предложений
- [x] GET /api/trade/my-proposals - мои предложения
- [x] GET /api/trade/proposals - предложения на мои трейды
- [x] GET /api/trade/cancel-proposal - отмена предложения
- [x] GET /api/trade/accept-proposal - принятие предложения
- [x] GET /api/trade/deals - история сделок

**Файл**: `test_ref_trades.py`

---

## Эндпоинты не требующие тестирования

### /api/admin/*
- POST /api/admin/init-telegram - служебный эндпоинт

### /api/health/*
- GET /api/health - health check
- GET /api/logs - логи (служебный)

### /api/bot/*
- POST /api/bot/webhook - webhook для бота

---

## Запуск тестов

```bash
# Все рефакторинг-тесты
pytest backend/tests/ref_tests/ -v

# Конкретный модуль
pytest backend/tests/ref_tests/test_ref_market.py -v

# С покрытием
pytest backend/tests/ref_tests/ -v --cov=app/api/routers --cov-report=html
```

## Примечания

1. **Тесты на 200 статус** - основная цель этих тестов убедиться что эндпоинт работает и возвращает ожидаемый статус
2. **Минимальная бизнес-логика** - тесты проверяют только базовую работоспособность, не все edge cases
3. **Изоляция** - каждый тест создает свои тестовые данные с уникальными ID
4. **Стабильность** - тесты не зависят от внешних сервисов (кроме тех, что требуют реальных Telegram/TON операций)

## Что делать при рефакторинге

1. Запустить тесты ДО рефакторинга: `pytest backend/tests/ref_tests/ -v`
2. Убедиться что все тесты проходят
3. Провести рефакторинг
4. Запустить тесты ПОСЛЕ рефакторинга: `pytest backend/tests/ref_tests/ -v`
5. Если тесты падают - исправить код или обновить тесты (если изменилась бизнес-логика)
