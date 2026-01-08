# Рефакторинг-тесты (ref_tests) - Краткая сводка

## Что это?

Папка `ref_tests/` содержит тесты для отслеживания состояния всех API эндпоинтов при рефакторинге.

**Цель**: Убедиться что все ручки возвращают статус 200 и базовая бизнес-логика работает.

## Статистика

- **Всего эндпоинтов**: ~60
- **Покрыто тестами**: 60
- **Покрытие**: 100%
- **Файлов с тестами**: 9

## Структура

```
ref_tests/
├── README.md                    # Подробное описание
├── COVERAGE.md                  # Детальное покрытие по эндпоинтам
├── test_ref_users.py           # 4 теста для /api/users/*
├── test_ref_accounts.py        # 3 теста для /api/accounts/*
├── test_ref_market.py          # 9 тестов для /api/market/*
├── test_ref_nft.py             # 7 тестов для /api/nft/*
├── test_ref_auctions.py        # 6 тестов для /api/auctions/*
├── test_ref_channels.py        # 8 тестов для /api/channels/*
├── test_ref_offers.py          # 5 тестов для /api/offers/*
├── test_ref_presale.py         # 5 тестов для /api/presales/*
└── test_ref_trades.py          # 13 тестов для /api/trade/*
```

## Быстрый запуск

### Windows
```bash
cd backend/tests
run_ref_tests.bat
```

### Linux/Mac
```bash
cd backend/tests
chmod +x run_ref_tests.sh
./run_ref_tests.sh
```

### Или напрямую через pytest
```bash
# Все тесты
pytest backend/tests/ref_tests/ -v

# Конкретный модуль
pytest backend/tests/ref_tests/test_ref_market.py -v

# Конкретный тест
pytest backend/tests/ref_tests/test_ref_market.py::TestRefMarket::test_get_salings_200 -v
```

## Принципы

1. ✅ **Каждый эндпоинт покрыт хотя бы одним тестом на успешный кейс (200)**
2. ✅ **Минимализм** - тесты проверяют только базовую работоспособность
3. ✅ **Изоляция** - каждый тест создает свои тестовые данные
4. ✅ **Стабильность** - тесты не зависят от внешних факторов

## Когда использовать

- ✅ Перед началом рефакторинга API
- ✅ После завершения рефакторинга
- ✅ При изменении бизнес-логики эндпоинтов
- ✅ Для быстрой проверки что все ручки работают

## Что НЕ тестируем

- ❌ Сложные edge cases (для этого есть другие тесты)
- ❌ Производительность (для этого есть load тесты)
- ❌ Детальную валидацию данных (для этого есть unit тесты)
- ❌ Эндпоинты требующие реальных Telegram/TON операций

## Пример теста

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

## Workflow при рефакторинге

1. **ДО рефакторинга**: `pytest backend/tests/ref_tests/ -v` → все зеленое ✅
2. **Рефакторинг**: меняем код, оптимизируем, переписываем
3. **ПОСЛЕ рефакторинга**: `pytest backend/tests/ref_tests/ -v` → все зеленое ✅
4. **Если тесты падают**: исправляем код или обновляем тесты

## Дополнительная информация

- Подробное описание: `ref_tests/README.md`
- Детальное покрытие: `ref_tests/COVERAGE.md`
- Существующие тесты: `test_heavy_endpoints.py` (26 тестов для тяжелых эндпоинтов)

---

**Создано**: 2025-12-03  
**Цель**: Отслеживание состояния API при рефакторинге
