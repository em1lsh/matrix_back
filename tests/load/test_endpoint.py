"""Quick test to check if endpoints work"""

import pymysql
import requests


# Get a test token
conn = pymysql.connect(
    host="localhost", port=3307, user="loadtest_user", password="LoadTest2024!SecurePass", database="loadtest_db"
)
cursor = conn.cursor()
cursor.execute("SELECT token FROM users LIMIT 1")
token = cursor.fetchone()[0]
conn.close()

print(f"Using token: {token[:20]}...")

# Test market endpoint
url = f"http://localhost:8001/market/?token={token}"
headers = {"Content-Type": "application/json"}
data = {
    "titles": [],
    "models": [],
    "patterns": [],
    "backdrops": [],
    "num": None,
    "sort": "price/desc",
    "page": 0,
    "count": 20,
}

response = requests.post(url, headers=headers, json=data)
print(f"\nMarket Status: {response.status_code}")
print(f"Market Response: {response.text[:500]}")

# Test accounts endpoint
url2 = f"http://localhost:8001/accounts?token={token}"
response2 = requests.get(url2, headers=headers)
print(f"\nAccounts Status: {response2.status_code}")
print(f"Accounts Response: {response2.text[:200]}")
