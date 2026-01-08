"""
Locust load testing scenarios for Matrix Backend - V2
Fixed to use correct URLs and token auth
"""

import random

import psycopg2
import psycopg2.extras
from locust import HttpUser, between, events, task


# Global token cache
_test_tokens = []


def load_tokens_from_db():
    """Load test tokens from database"""
    global _test_tokens
    if _test_tokens:
        return _test_tokens

    try:
        conn = psycopg2.connect(
            host="127.0.0.1",  # Use IPv4 explicitly
            port=5433,
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
        _test_tokens = []

    return _test_tokens


class MarketUser(HttpUser):
    """
    Simulates a user interacting with the market
    """

    wait_time = between(1, 3)
    host = "http://127.0.0.1:8001"

    def on_start(self):
        """Called when a user starts"""
        tokens = load_tokens_from_db()
        self.token = random.choice(tokens)

    @task(15)
    def get_market_items(self):
        """Get market items list"""
        self.client.post(
            f"/market/?token={self.token}",
            json={
                "titles": [],
                "models": [],
                "patterns": [],
                "backdrops": [],
                "num": None,
                "sort": random.choice(["price/desc", "price/asc", "num/desc"]),
                "page": random.randint(0, 10),
                "count": 20,
            },
            name="POST /market/ (list items)",
        )

    @task(5)
    def get_market_with_filters(self):
        """Get market items with filters"""
        titles = ["Delicious Cake", "Blue Star", "Red Heart", "Green Clover", "Golden Crown"]
        self.client.post(
            f"/market/?token={self.token}",
            json={
                "titles": random.sample(titles, random.randint(1, 3)),
                "models": [],
                "patterns": [],
                "backdrops": [],
                "num": None,
                "sort": "price/desc",
                "page": 0,
                "count": 20,
            },
            name="POST /market/ (with filters)",
        )

    @task(8)
    def get_accounts(self):
        """Get user accounts"""
        self.client.get(f"/accounts?token={self.token}", name="GET /accounts")

    @task(6)
    def get_my_nfts(self):
        """Get user's NFTs"""
        self.client.get(f"/nft/my?token={self.token}", name="GET /nft/my")

    @task(4)
    def get_collections(self):
        """Get collections filter"""
        self.client.get(f"/market/collections?token={self.token}", name="GET /market/collections")

    @task(3)
    def get_patterns(self):
        """Get patterns filter"""
        self.client.post(
            f"/market/patterns?token={self.token}", json=["Delicious Cake", "Blue Star"], name="POST /market/patterns"
        )

    @task(3)
    def get_models(self):
        """Get models filter"""
        self.client.post(
            f"/market/models?token={self.token}", json=["Delicious Cake", "Blue Star"], name="POST /market/models"
        )

    @task(2)
    def get_backdrops(self):
        """Get backdrops filter"""
        self.client.post(f"/market/backdrops?token={self.token}", json={}, name="POST /market/backdrops")

    @task(2)
    def get_integrations(self):
        """Get market integrations"""
        self.client.get(f"/market/integrations?token={self.token}", name="GET /market/integrations")

    @task(2)
    def get_my_offers(self):
        """Get user's offers"""
        self.client.get(f"/offers/my?token={self.token}", name="GET /offers/my")

    @task(2)
    def get_nft_sells(self):
        """Get NFT sell history"""
        self.client.get(f"/nft/sells?token={self.token}", name="GET /nft/sells")

    @task(2)
    def get_nft_buys(self):
        """Get NFT buy history"""
        self.client.get(f"/nft/buys?token={self.token}", name="GET /nft/buys")

    @task(1)
    def get_presales(self):
        """Get presales"""
        self.client.post(
            f"/presale/?token={self.token}",
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
            name="POST /presale/ (list)",
        )

    @task(1)
    def get_auctions(self):
        """Get auctions"""
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
            name="POST /auctions/ (list)",
        )

    @task(1)
    def get_my_auctions(self):
        """Get user's auctions"""
        self.client.get(f"/auctions/my?token={self.token}", name="GET /auctions/my")

    @task(1)
    def get_auction_deals(self):
        """Get auction deals history"""
        self.client.get(f"/auctions/deals?token={self.token}", name="GET /auctions/deals")

    @task(3)
    def get_trades(self):
        """Get trades list"""
        self.client.post(
            f"/trade/?token={self.token}",
            json={"sended_requirements": None, "gived_requirements": None},
            name="POST /trade/ (list)",
        )

    @task(2)
    def get_my_trades(self):
        """Get user's trades"""
        self.client.get(f"/trade/my?token={self.token}", name="GET /trade/my")

    @task(1)
    def get_personal_trades(self):
        """Get personal trades"""
        self.client.get(f"/trade/personal?token={self.token}", name="GET /trade/personal")

    @task(1)
    def get_my_trade_proposals(self):
        """Get user's trade proposals"""
        self.client.get(f"/trade/my-proposals?token={self.token}", name="GET /trade/my-proposals")

    @task(1)
    def get_trade_proposals(self):
        """Get proposals on user's trades"""
        self.client.get(f"/trade/proposals?token={self.token}", name="GET /trade/proposals")

    @task(1)
    def get_trade_deals(self):
        """Get trade deals history"""
        self.client.get(f"/trade/deals?token={self.token}", name="GET /trade/deals")

    @task(2)
    def get_user_info(self):
        """Get user information"""
        self.client.get(f"/users/me?token={self.token}", name="GET /users/me")

    @task(1)
    def get_balance_topups(self):
        """Get balance topup history"""
        self.client.get(f"/users/balance-topups?token={self.token}", name="GET /users/balance-topups")

    @task(1)
    def get_nft_deals(self):
        """Get NFT deals for specific gift"""
        gift_id = random.randint(1, 200)
        self.client.get(f"/nft/deals?gift_id={gift_id}&token={self.token}", name="GET /nft/deals")

    @task(2)
    def get_user_topups(self):
        """Get user topups history"""
        self.client.get(f"/users/topups?token={self.token}", name="GET /users/topups")

    @task(2)
    def get_user_withdraws(self):
        """Get user withdraws history"""
        self.client.get(f"/users/withdraws?token={self.token}", name="GET /users/withdraws")

    @task(3)
    def get_market_floor(self):
        """Get market floor price"""
        models = ["Delicious Cake", "Blue Star", "Red Heart", "Green Clover"]
        self.client.post(
            f"/market/floor?token={self.token}",
            json={"name": random.choice(models), "time_range": "7"},
            name="POST /market/floor",
        )

    @task(2)
    def get_market_charts(self):
        """Get market price charts"""
        models = ["Delicious Cake", "Blue Star", "Red Heart"]
        self.client.post(
            f"/market/charts?token={self.token}",
            json={"name": random.choice(models), "time_range": "7"},
            name="POST /market/charts",
        )

    @task(1)
    def get_topup_balance_info(self):
        """Get topup balance information"""
        self.client.get(f"/market/topup-balance?ton_amount=10&token={self.token}", name="GET /market/topup-balance")

    @task(1)
    def get_presales_list(self):
        """Get presales list"""
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
            name="POST /presales/ (list)",
        )

    @task(1)
    def get_my_presales(self):
        """Get user's presales"""
        self.client.get(f"/presales/my?token={self.token}", name="GET /presales/my")


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
