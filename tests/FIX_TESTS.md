# Как исправить тесты

## Проблема

Тесты используют `headers={"token": test_token}`, но `get_current_user` ожидает токен в query параметрах.

## Решение

Заменить все:
```python
headers={"token": test_token}
```

На добавление токена в params:
```python
params={..., "token": test_token}
```

## Примеры

### GET запросы

**Было:**
```python
response = await client.get(
    "/api/market/collections",
    headers={"token": test_token}
)
```

**Стало:**
```python
response = await client.get(
    "/api/market/collections",
    params={"token": test_token}
)
```

### GET с params

**Было:**
```python
response = await client.get(
    "/api/market/output",
    headers={"token": test_token},
    params={
        "ton_amount": 10.0,
        "address": "EQTest123"
    }
)
```

**Стало:**
```python
response = await client.get(
    "/api/market/output",
    params={
        "ton_amount": 10.0,
        "address": "EQTest123",
        "token": test_token  # Добавить токен в params
    }
)
```

### POST запросы

**Было:**
```python
response = await client.post(
    "/api/market/",
    headers={"token": test_token},
    json={...}
)
```

**Стало:**
```python
response = await client.post(
    "/api/market/",
    params={"token": test_token},  # token в params
    json={...}
)
```

### DELETE запросы

**Было:**
```python
response = await client.delete(
    "/api/accounts",
    headers={"token": test_token},
    params={"account_id": "test_id"}
)
```

**Стало:**
```python
response = await client.delete(
    "/api/accounts",
    params={
        "account_id": "test_id",
        "token": test_token  # Добавить токен
    }
)
```

## Автоматическая замена (PowerShell)

```powershell
cd backend/tests
(Get-Content test_heavy_endpoints.py) -replace 'headers=\{"token": test_token\}', 'params={"token": test_token}' | Set-Content test_heavy_endpoints.py
```

## Проверка

После исправления запустить:
```bash
poetry run pytest tests/test_heavy_endpoints.py -v
```

Все тесты должны проходить!
