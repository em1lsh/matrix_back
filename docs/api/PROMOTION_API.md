# API продвижения NFT

## Обзор

Система продвижения NFT позволяет пользователям продвигать свои NFT за плату. Продвинутые NFT получают приоритет в отображении и больше видимости.

## Основные возможности

- **Расчет стоимости**: Получить стоимость продвижения с учетом скидок
- **Продвижение NFT**: Создать новое продвижение
- **Продление продвижения**: Продлить существующее или создать новое

## Ценообразование

- **Базовая стоимость**: 0.1 TON за день (настраивается через `NFT_PROMOTION_DAILY_COST`)
- **Система скидок**: 5% за каждый дополнительный день, максимум 20%
- **Формула скидки**: `min(0.05 * (days - 1), 0.20)`

### Примеры цен

| Дни | Базовая стоимость | Скидка | Итоговая стоимость | Экономия |
|-----|-------------------|--------|-------------------|----------|
| 1   | 0.10 TON         | 0%     | 0.10 TON          | 0.00 TON |
| 2   | 0.20 TON         | 5%     | 0.19 TON          | 0.01 TON |
| 5   | 0.50 TON         | 20%    | 0.40 TON          | 0.10 TON |
| 10  | 1.00 TON         | 20%    | 0.80 TON          | 0.20 TON |
| 30  | 3.00 TON         | 20%    | 2.40 TON          | 0.60 TON |

## Эндпоинты

### POST /promotion/calculate

Рассчитать стоимость продвижения NFT.

**Запрос:**
```json
{
  "days": 7
}
```

**Ответ:**
```json
{
  "days": 7,
  "base_cost_ton": 0.70,
  "discount_percent": 20.0,
  "final_cost_ton": 0.56,
  "savings_ton": 0.14
}
```

**Параметры:**
- `days` (int): Количество дней продвижения (1-30)

### POST /promotion/promote

Продвинуть NFT.

**Запрос:**
```json
{
  "nft_id": 123,
  "days": 7
}
```

**Ответ:**
```json
{
  "success": true,
  "promotion": {
    "id": 1,
    "nft_id": 123,
    "user_id": 456,
    "created_at": "2025-12-16T18:00:00Z",
    "ends_at": "2025-12-23T18:00:00Z",
    "total_costs_ton": 0.56,
    "is_active": true
  },
  "cost_ton": 0.56,
  "new_balance_ton": 1.44
}
```

**Требования:**
- NFT должен принадлежать пользователю
- У пользователя должно быть достаточно средств
- NFT не должен иметь активного продвижения

**Ошибки:**
- `404` - NFT не найден
- `403` - NFT не принадлежит пользователю
- `409` - NFT уже имеет активное продвижение
- `402` - Недостаточно средств
- `400` - Неверный период продвижения

### POST /promotion/extend

Продлить продвижение NFT.

**Запрос:**
```json
{
  "nft_id": 123,
  "days": 5
}
```

**Ответ:**
```json
{
  "success": true,
  "promotion": {
    "id": 1,
    "nft_id": 123,
    "user_id": 456,
    "created_at": "2025-12-16T18:00:00Z",
    "ends_at": "2025-12-28T18:00:00Z",
    "total_costs_ton": 0.96,
    "is_active": true
  },
  "cost_ton": 0.40,
  "new_balance_ton": 1.04
}
```

**Особенности:**
- Если активного продвижения нет, создает новое
- Если есть активное продвижение, продлевает его
- Если продвижение истекло, создает новое

## Бизнес-логика

### Автоматическая деактивация

- Продвижения автоматически деактивируются при истечении срока
- Фоновая задача проверяет истекшие продвижения каждые 10 минут
- При покупке NFT его продвижение автоматически деактивируется

### Ограничения

- Только одно активное продвижение на NFT
- Максимальный период продвижения: 30 дней
- Минимальный период продвижения: 1 день

### База данных

Таблица `promoted_nfts`:
```sql
CREATE TABLE promoted_nfts (
    id SERIAL PRIMARY KEY,
    nft_id INTEGER NOT NULL REFERENCES nfts(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    ends_at TIMESTAMP NOT NULL,
    total_costs BIGINT NOT NULL, -- в nanotons
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Индексы для производительности
    INDEX(nft_id, is_active),
    INDEX(user_id, is_active),
    INDEX(ends_at),
    
    -- Уникальный индекс для активных продвижений
    UNIQUE INDEX(nft_id) WHERE is_active = TRUE
);
```

## Интеграция

### Модуль NFT

При покупке NFT автоматически деактивируется его продвижение:

```python
# В BuyNFTUseCase
from app.modules.promotion.repository import PromotionRepository

promotion_repo = PromotionRepository(session)
await promotion_repo.deactivate_promotion(nft_id)
```

### Фоновые задачи

Для запуска очистки истекших продвижений:

```python
from app.modules.promotion.tasks import promotion_cleanup_scheduler

# Запуск в фоновом режиме
asyncio.create_task(promotion_cleanup_scheduler())
```

## Конфигурация

Переменные окружения:

```env
# Стоимость продвижения NFT за день (в nanotons)
NFT_PROMOTION_DAILY_COST=100000000  # 0.1 TON
```