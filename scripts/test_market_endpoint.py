"""
Тестовый скрипт для проверки /market/ эндпоинта
"""

import json

import requests


# URL эндпоинта
url = "http://127.0.0.1:8000/market/"

# Токен из запроса
token = "1764849484_0d9ce96b-0b7e-425e-bf29-3b337e197c35"

# Данные запроса
payload = {
    "backdrops": [],
    "count": 50000,
    "models": [],
    "num": 0,
    "page": 0,
    "patterns": [],
    "price_max": 0,
    "price_min": 0,
    "sort": "price/asc",
    "titles": [],
}

# Заголовки
headers = {"Content-Type": "application/json"}

# Добавляем токен в URL
full_url = f"{url}?token={token}"

print(f"Отправка запроса на: {full_url}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(full_url, json=payload, headers=headers)

    print(f"\nСтатус код: {response.status_code}")
    print(f"Заголовки ответа: {dict(response.headers)}")

    if response.status_code == 200:
        print("\n✓ Успешный ответ!")
        data = response.json()
        print(f"Получено записей: {len(data)}")
        if data:
            print(f"Первая запись: {json.dumps(data[0], indent=2, ensure_ascii=False)}")
    else:
        print("\n✗ Ошибка!")
        print(f"Ответ: {response.text}")

except Exception as e:
    print(f"\n✗ Исключение: {e}")
