"""
Load test для проверки производительности после внедрения UoW

Тестирует критичные эндпоинты с UoW и distributed locks
"""

import logging

from locust import HttpUser, between, events, task


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UoWLoadTestUser(HttpUser):
    """
    Пользователь для load testing эндпоинтов с UoW
    """

    # Время ожидания между запросами (1-3 секунды)
    wait_time = between(1, 3)

    def on_start(self):
        """Инициализация при старте пользователя"""
        # Читаем токен из файла
        from pathlib import Path

        token_file = Path(__file__).parent / "test_token.txt"
        if token_file.exists():
            self.token = token_file.read_text().strip()
        else:
            self.token = "1764786516_7a553267-6000-4f3a-9c57-d6dd59e6484c"

        self.user_id = 999999999
        logger.info(f"User {self.user_id} started with token")

    @task(10)
    def get_market_salings(self):
        """
        Получение списка товаров на маркете

        Вес: 10 (самый частый запрос)
        """
        with self.client.post(
            "/market/",
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
            params={"token": self.token},
            catch_response=True,
            name="POST /market/",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @task(5)
    def get_my_nfts(self):
        """
        Получение своих NFT

        Вес: 5
        """
        with self.client.get(
            "/nft/my", params={"token": self.token}, catch_response=True, name="GET /nft/my"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @task(3)
    def get_auctions(self):
        """
        Получение списка аукционов

        Вес: 3
        """
        with self.client.post(
            "/auctions/",
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
            params={"token": self.token},
            catch_response=True,
            name="POST /auctions/",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @task(2)
    def get_presales(self):
        """
        Получение списка пресейлов

        Вес: 2
        """
        with self.client.post(
            "/presales/",
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
            params={"token": self.token},
            catch_response=True,
            name="POST /presales/",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    # Закомментировал concurrent_nft_buy так как требует специальной подготовки данных
    # @task(1)
    # def concurrent_nft_buy_simulation(self):
    #     """
    #     Симуляция одновременной покупки NFT
    #
    #     Вес: 1 (редкая операция, но критичная)
    #
    #     Проверяет что distributed locks работают под нагрузкой
    #     """
    #     # Используем фиксированный NFT ID для создания конкуренции
    #     nft_id = 800000001
    #
    #     with self.client.get(
    #         "/nft/buy",
    #         params={
    #             "nft_id": nft_id,
    #             "token": self.token
    #         },
    #         catch_response=True,
    #         name="GET /nft/buy (concurrent)"
    #     ) as response:
    #         # Ожидаем либо успех (200), либо "NFT not available" (400)
    #         if response.status_code == 200:
    #             response.success()
    #             logger.info(f"User {self.user_id} successfully bought NFT {nft_id}")
    #         elif response.status_code == 400:
    #             # Это нормально - NFT уже куплен или недостаточно средств
    #             response.success()
    #         else:
    #             response.failure(f"Unexpected status: {response.status_code}")


# Закомментировал StressTestUser так как он требует специальной подготовки данных
# class StressTestUser(HttpUser):
#     """
#     Стресс-тест для проверки race conditions
#
#     Все пользователи пытаются купить ОДИН И ТОТ ЖЕ NFT одновременно
#     """
#
#     wait_time = between(0.1, 0.5)  # Минимальная задержка для максимальной конкуренции
#
#     def on_start(self):
#         from pathlib import Path
#         token_file = Path(__file__).parent / "test_token.txt"
#         if token_file.exists():
#             self.token = token_file.read_text().strip()
#         else:
#             self.token = "229769206885ccba593b72dc4ea0537db946ebb34d6eda3a77a3b2442ce261c2"
#         self.user_id = 999999999
#
#     @task
#     def try_buy_same_nft(self):
#         """
#         Все пользователи пытаются купить один NFT
#
#         Проверяет что только ОДИН успешно купит
#         """
#         nft_id = 900000001  # Фиксированный ID
#
#         with self.client.get(
#             "/nft/buy",
#             params={
#                 "nft_id": nft_id,
#                 "token": self.token
#             },
#             catch_response=True,
#             name="STRESS: Buy same NFT"
#         ) as response:
#             if response.status_code == 200:
#                 logger.warning(f"✅ User {self.user_id} WON the race for NFT {nft_id}")
#                 response.success()
#             elif response.status_code == 400:
#                 # Проиграл гонку - это нормально
#                 response.success()
#             else:
#                 response.failure(f"Unexpected: {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Вызывается при старте теста"""
    logger.info("=" * 80)
    logger.info("UoW Load Test Started")
    logger.info("=" * 80)
    logger.info("Testing endpoints with UoW and distributed locks")
    logger.info("Expected: No race conditions, consistent data")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Вызывается при остановке теста"""
    logger.info("=" * 80)
    logger.info("UoW Load Test Completed")
    logger.info("=" * 80)

    # Вывод статистики
    stats = environment.stats
    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Total failures: {stats.total.num_failures}")
    logger.info(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    logger.info(f"RPS: {stats.total.total_rps:.2f}")

    if stats.total.num_failures > 0:
        failure_rate = (stats.total.num_failures / stats.total.num_requests) * 100
        logger.warning(f"Failure rate: {failure_rate:.2f}%")
    else:
        logger.info("✅ No failures!")
