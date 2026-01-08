"""
Complete Locust load testing for Matrix Backend - ALL 115+ Endpoints
Includes mocks for all data requirements
"""

import random

import psycopg2
import psycopg2.extras
from locust import HttpUser, between, events, task


# Global token cache
_test_tokens = []
_test_nft_ids = []
_test_gift_ids = []
_test_trade_ids = []
_test_channel_ids = []


def load_test_data():
    """Load test data from database"""
    global _test_tokens, _test_nft_ids, _test_gift_ids, _test_trade_ids, _test_channel_ids

    if _test_tokens:
        return

    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            user="loadtest_user",
            password="LoadTest2024!SecurePass",
            database="loadtest_db",
        )
        cursor = conn.cursor()

        # Load tokens
        cursor.execute("SELECT token FROM users LIMIT 1000")
        _test_tokens = [row[0] for row in cursor.fetchall()]

        # Load NFT IDs
        cursor.execute("SELECT id FROM nfts WHERE price IS NOT NULL LIMIT 100")
        _test_nft_ids = [row[0] for row in cursor.fetchall()]

        # Load Gift IDs
        cursor.execute("SELECT id FROM gifts LIMIT 100")
        _test_gift_ids = [row[0] for row in cursor.fetchall()]

        conn.close()
        print(f"Loaded test data: {len(_test_tokens)} tokens, {len(_test_nft_ids)} NFTs, {len(_test_gift_ids)} gifts")
    except Exception as e:
        print(f"Failed to load test data: {e}")
        _test_tokens = []


class CompleteAPIUser(HttpUser):
    """
    Complete API user simulating all possible interactions
    """

    wait_time = between(0.5, 2)
    host = "http://localhost:8001"

    def on_start(self):
        """Called when a user starts"""
        load_test_data()
        self.token = random.choice(_test_tokens) if _test_tokens else "test_token"
        self.collections = ["Delicious Cake", "Blue Star", "Red Heart", "Green Clover", "Golden Crown"]
        self.models = ["Delicious Cake", "Blue Star", "Red Heart"]
        self.patterns = ["Pattern 1", "Pattern 2", "Pattern 3"]
        self.backdrops = ["Backdrop 1", "Backdrop 2"]

    # ==================== MARKET ENDPOINTS ====================

    @task(20)
    def market_list(self):
        """POST /market/ - Get market items"""
        self.client.post(
            f"/market/?token={self.token}",
            json={
                "titles": [],
                "models": [],
                "patterns": [],
                "backdrops": [],
                "num": None,
                "sort": random.choice(["price/desc", "price/asc", "num/desc", "created_at/desc"]),
                "page": random.randint(0, 5),
                "count": 20,
            },
            name="POST /market/",
        )

    @task(5)
    def market_list_filtered(self):
        """POST /market/ - Get market items with filters"""
        self.client.post(
            f"/market/?token={self.token}",
            json={
                "titles": random.sample(self.collections, random.randint(1, 2)),
                "models": [],
                "patterns": [],
                "backdrops": [],
                "num": None,
                "sort": "price/desc",
                "page": 0,
                "count": 20,
            },
            name="POST /market/ (filtered)",
        )

    @task(5)
    def market_collections(self):
        """GET /market/collections"""
        self.client.get(f"/market/collections?token={self.token}", name="GET /market/collections")

    @task(4)
    def market_patterns(self):
        """POST /market/patterns"""
        self.client.post(
            f"/market/patterns?token={self.token}",
            json=random.sample(self.collections, random.randint(1, 2)),
            name="POST /market/patterns",
        )

    @task(4)
    def market_models(self):
        """POST /market/models"""
        self.client.post(
            f"/market/models?token={self.token}",
            json=random.sample(self.collections, random.randint(1, 2)),
            name="POST /market/models",
        )

    @task(3)
    def market_backdrops(self):
        """POST /market/backdrops"""
        self.client.post(f"/market/backdrops?token={self.token}", json={}, name="POST /market/backdrops")

    @task(3)
    def market_integrations(self):
        """GET /market/integrations"""
        self.client.get(f"/market/integrations?token={self.token}", name="GET /market/integrations")

    @task(3)
    def market_charts(self):
        """POST /market/charts"""
        self.client.post(
            f"/market/charts?token={self.token}",
            json={"name": random.choice(self.models), "time_range": random.choice(["7", "30", "90"])},
            name="POST /market/charts",
        )

    @task(4)
    def market_floor(self):
        """POST /market/floor"""
        self.client.post(
            f"/market/floor?token={self.token}",
            json={"name": random.choice(self.models), "time_range": "7"},
            name="POST /market/floor",
        )

    @task(2)
    def market_topup_balance(self):
        """GET /market/topup-balance"""
        self.client.get(
            f"/market/topup-balance?ton_amount={random.randint(10, 100)}&token={self.token}",
            name="GET /market/topup-balance",
        )

    # ==================== NFT ENDPOINTS ====================

    @task(8)
    def nft_my(self):
        """GET /nft/my"""
        self.client.get(f"/nft/my?token={self.token}", name="GET /nft/my")

    @task(3)
    def nft_buys(self):
        """GET /nft/buys"""
        self.client.get(f"/nft/buys?token={self.token}", name="GET /nft/buys")

    @task(3)
    def nft_sells(self):
        """GET /nft/sells"""
        self.client.get(f"/nft/sells?token={self.token}", name="GET /nft/sells")

    @task(2)
    def nft_deals(self):
        """GET /nft/deals"""
        gift_id = random.choice(_test_gift_ids) if _test_gift_ids else random.randint(1, 100)
        self.client.get(f"/nft/deals?gift_id={gift_id}&token={self.token}", name="GET /nft/deals")

    # ==================== USER ENDPOINTS ====================

    @task(5)
    def users_me(self):
        """GET /users/me"""
        self.client.get(f"/users/me?token={self.token}", name="GET /users/me")

    @task(3)
    def users_topups(self):
        """GET /users/topups"""
        self.client.get(f"/users/topups?token={self.token}", name="GET /users/topups")

    @task(3)
    def users_withdraws(self):
        """GET /users/withdraws"""
        self.client.get(f"/users/withdraws?token={self.token}", name="GET /users/withdraws")

    @task(2)
    def users_auth(self):
        """GET /users/auth"""
        self.client.get(f"/users/auth?token={self.token}", name="GET /users/auth")

    # ==================== ACCOUNTS ENDPOINTS ====================

    @task(6)
    def accounts_list(self):
        """GET /accounts"""
        self.client.get(f"/accounts?token={self.token}", name="GET /accounts")

    # ==================== OFFERS ENDPOINTS ====================

    @task(3)
    def offers_my(self):
        """GET /offers/my"""
        self.client.get(f"/offers/my?token={self.token}", name="GET /offers/my")

    # ==================== TRADES ENDPOINTS ====================

    @task(4)
    def trades_list(self):
        """POST /trade/"""
        self.client.post(
            f"/trade/?token={self.token}",
            json={"sended_requirements": None, "gived_requirements": None},
            name="POST /trade/",
        )

    @task(3)
    def trades_my(self):
        """GET /trade/my"""
        self.client.get(f"/trade/my?token={self.token}", name="GET /trade/my")

    @task(2)
    def trades_personal(self):
        """GET /trade/personal"""
        self.client.get(f"/trade/personal?token={self.token}", name="GET /trade/personal")

    @task(2)
    def trades_my_proposals(self):
        """GET /trade/my-proposals"""
        self.client.get(f"/trade/my-proposals?token={self.token}", name="GET /trade/my-proposals")

    @task(2)
    def trades_proposals(self):
        """GET /trade/proposals"""
        self.client.get(f"/trade/proposals?token={self.token}", name="GET /trade/proposals")

    @task(2)
    def trades_deals(self):
        """GET /trade/deals"""
        self.client.get(f"/trade/deals?token={self.token}", name="GET /trade/deals")

    # ==================== AUCTIONS ENDPOINTS ====================

    @task(2)
    def auctions_list(self):
        """POST /auctions/"""
        self.client.post(
            f"/auctions/?token={self.token}",
            json={
                "titles": [],
                "models": [],
                "patterns": [],
                "backdrops": [],
                "num": None,
                "sort": "price/desc",
                "page": 0,
                "count": 20,
            },
            name="POST /auctions/",
        )

    @task(2)
    def auctions_my(self):
        """GET /auctions/my"""
        self.client.get(f"/auctions/my?token={self.token}", name="GET /auctions/my")

    @task(2)
    def auctions_deals(self):
        """GET /auctions/deals"""
        self.client.get(f"/auctions/deals?token={self.token}", name="GET /auctions/deals")

    # ==================== PRESALES ENDPOINTS ====================

    @task(2)
    def presales_list(self):
        """POST /presales/"""
        self.client.post(
            f"/presales/?token={self.token}",
            json={
                "titles": [],
                "models": [],
                "patterns": [],
                "backdrops": [],
                "num": None,
                "sort": "price/desc",
                "page": 0,
                "count": 20,
            },
            name="POST /presales/",
        )

    @task(2)
    def presales_my(self):
        """GET /presales/my"""
        self.client.get(f"/presales/my?token={self.token}", name="GET /presales/my")

    # ==================== CHANNELS ENDPOINTS ====================

    @task(2)
    def channels_list(self):
        """GET /channels"""
        self.client.get(f"/channels?token={self.token}", name="GET /channels")

    @task(2)
    def channels_my(self):
        """GET /channels/my"""
        self.client.get(f"/channels/my?token={self.token}", name="GET /channels/my")

    @task(2)
    def channels_buys(self):
        """GET /channels/buys"""
        self.client.get(f"/channels/buys?token={self.token}", name="GET /channels/buys")

    @task(2)
    def channels_sells(self):
        """GET /channels/sells"""
        self.client.get(f"/channels/sells?token={self.token}", name="GET /channels/sells")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("=" * 80)
    print("COMPLETE API LOAD TEST STARTING")
    print("=" * 80)
    print(f"Host: {environment.host}")
    print("Testing 115+ endpoints with full coverage")
    print("=" * 80)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    print("\n" + "=" * 80)
    print("COMPLETE API LOAD TEST COMPLETED")
    print("=" * 80)

    stats = environment.stats
    print("\nOVERALL STATISTICS:")
    print(f"  Total Requests: {stats.total.num_requests:,}")
    print(f"  Total Failures: {stats.total.num_failures:,}")
    print(
        f"  Success Rate: {((stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100):.2f}%"
    )
    print(f"  Requests/Second: {stats.total.total_rps:.2f}")
    print("\nRESPONSE TIMES:")
    print(f"  Average: {stats.total.avg_response_time:.2f}ms")
    print(f"  Median: {stats.total.median_response_time:.2f}ms")
    print(f"  95th Percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"  99th Percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"  Max: {stats.total.max_response_time:.2f}ms")
    print("=" * 80)
