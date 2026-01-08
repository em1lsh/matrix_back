"""
Locust load testing scenarios for Matrix Backend
"""

import random
import sys
from pathlib import Path

import pymysql
from locust import HttpUser, between, events, task


# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project"))

# Global token cache
_test_tokens = []


def load_tokens_from_db():
    """Load test tokens from database"""
    global _test_tokens
    if _test_tokens:
        return _test_tokens

    try:
        conn = pymysql.connect(
            host="localhost",
            port=3307,
            user="loadtest_user",
            password="LoadTest2024!SecurePass",
            database="loadtest_db",
        )
        cursor = conn.cursor()
        cursor.execute("SELECT token FROM users LIMIT 1000")
        _test_tokens = [row[0] for row in cursor.fetchall()]
        conn.close()
        print(f"Loaded {len(_test_tokens)} tokens from database")
    except Exception as e:
        print(f"Failed to load tokens from database: {e}")
        _test_tokens = [f"test_token_{i}" for i in range(100)]

    return _test_tokens


class MarketUser(HttpUser):
    """
    Simulates a user interacting with the market
    """

    wait_time = between(1, 3)
    host = "http://localhost:8001"

    def on_start(self):
        """Called when a user starts"""
        # Get a random test token
        tokens = load_tokens_from_db()
        self.token = random.choice(tokens)

    @task(10)
    def get_market_items(self):
        """Get market items list"""
        self.client.post(
            "/api/market/",
            headers=self.headers,
            json={
                "titles": [],
                "models": [],
                "patterns": [],
                "backdrops": [],
                "num": None,
                "sort": "price/desc",
                "page": random.randint(0, 5),
                "count": 20,
            },
            name="POST /api/market/ (list items)",
        )

    @task(5)
    def get_accounts(self):
        """Get user accounts"""
        self.client.get("/api/accounts", headers=self.headers, name="GET /api/accounts")

    @task(3)
    def get_collections(self):
        """Get collections"""
        self.client.get("/api/market/collections", headers=self.headers, name="GET /api/market/collections")

    @task(3)
    def get_models(self):
        """Get models filter"""
        self.client.post(
            "/api/market/models",
            headers=self.headers,
            json=["Delicious Cake", "Blue Star"],
            name="POST /api/market/models",
        )

    @task(3)
    def get_patterns(self):
        """Get patterns filter"""
        self.client.post(
            "/api/market/patterns",
            headers=self.headers,
            json=["Delicious Cake", "Blue Star"],
            name="POST /api/market/patterns",
        )

    @task(2)
    def get_backdrops(self):
        """Get backdrops filter"""
        self.client.post("/api/market/backdrops", headers=self.headers, json={}, name="POST /api/market/backdrops")

    @task(2)
    def get_user_nfts(self):
        """Get user NFTs"""
        self.client.get("/api/accounts/gifts", headers=self.headers, name="GET /api/accounts/gifts")

    @task(1)
    def get_integrations(self):
        """Get market integrations"""
        self.client.get("/api/market/integrations", headers=self.headers, name="GET /api/market/integrations")

    @task(1)
    def health_check(self):
        """Health check endpoint"""
        self.client.get("/health", name="GET /health")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("Load test starting...")
    print(f"Host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    print("Load test completed!")

    # Print summary
    stats = environment.stats
    print(f"\nTotal requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Median response time: {stats.total.median_response_time:.2f}ms")
    print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"99th percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"Max response time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests per second: {stats.total.total_rps:.2f}")
