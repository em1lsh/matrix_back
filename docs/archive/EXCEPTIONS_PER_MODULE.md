# Исключения по модулям

**Дата:** 6 декабря 2025  
**Статус:** ✅ Завершено

---

## 🎯 Концепция

Каждый модуль имеет свои специфичные исключения, которые:
- Наследуются от базовых исключений `app.exceptions`
- Предоставляют понятные сообщения об ошибках
- Изолированы внутри модуля
- Легко тестируются

---

## 📁 Структура

```
modules/имя/
├── exceptions.py    # ✅ Специфичные исключения модуля
├── service.py       # Использует exceptions
├── use_cases.py     # Использует exceptions
└── router.py        # Обрабатываются автоматически
```

---

## 🔥 Исключения по модулям

### 1. NFT модуль
```python
# modules/nft/exceptions.py
- NFTNotFoundError
- NFTNotAvailableError
- NFTNotForSaleError
- NFTPermissionDeniedError
```

### 2. Market модуль
```python
# modules/market/exceptions.py
- InvalidTONAddressError
- WithdrawalFailedError
- InsufficientBalanceError
```

### 3. Offers модуль
```python
# modules/offers/exceptions.py
- OfferNotFoundError
- OfferPermissionDeniedError
```

### 4. Trades модуль
```python
# modules/trades/exceptions.py
- TradeNotFoundError
- TradePermissionDeniedError
- TradeProposalNotFoundError
- InvalidTradeRequirementsError
```

### 5. Presale модуль
```python
# modules/presale/exceptions.py
- PresaleNotFoundError
- PresalePermissionDeniedError
```

### 6. Channels модуль
```python
# modules/channels/exceptions.py
- ChannelNotFoundError
- ChannelPermissionDeniedError
- InvalidChannelUsernameError
```

### 7. Auctions модуль
```python
# modules/auctions/exceptions.py
- AuctionNotFoundError
- AuctionPermissionDeniedError
- AuctionExpiredError
- InvalidBidError
```

### 8. Accounts модуль
```python
# modules/accounts/exceptions.py
- AccountNotFoundError
- AccountPermissionDeniedError
- InvalidPhoneNumberError
- InvalidVerificationCodeError
```

### 9. Users модуль
```python
# modules/users/exceptions.py
- UserNotFoundError
- TokenNotFoundError
```

---

## 💡 Использование

### В Service
```python
# modules/nft/service.py
from .exceptions import NFTNotFoundError, NFTPermissionDeniedError

class NFTService:
    async def set_price(self, nft_id, user_id, price):
        nft = await self.repo.get_by_id(nft_id)
        if not nft:
            raise NFTNotFoundError(nft_id)
        
        if nft.user_id != user_id:
            raise NFTPermissionDeniedError(nft_id)
```

### В UseCase
```python
# modules/nft/use_cases.py
from .exceptions import NFTNotFoundError

class BuyNFTUseCase:
    async def execute(self, nft_id, buyer_id):
        nft = await self.repo.get_for_purchase(nft_id)
        if not nft:
            raise NFTNotFoundError(nft_id)
```

### Автоматическая обработка
Все исключения автоматически обрабатываются в `app/api/exception_handlers.py`:
- `NotFoundError` → 404
- `PermissionDeniedError` → 403
- `ValidationError` → 400
- `AuthenticationError` → 401

---

## ✅ Преимущества

1. **Изоляция** - каждый модуль имеет свои исключения
2. **Понятность** - четкие названия и сообщения
3. **Типизация** - IDE подсказывает доступные исключения
4. **Тестируемость** - легко проверить конкретное исключение
5. **Документация** - понятно какие ошибки может вернуть модуль

---

## 🎉 Итоги

- ✅ Создано 9 файлов exceptions.py
- ✅ 25+ специфичных исключений
- ✅ Все наследуются от базовых
- ✅ Автоматическая обработка
- ✅ Полная типизация

**Исключения изолированы по модулям!** 🚀
