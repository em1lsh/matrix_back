import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

from curl_cffi import requests

from app.configs import settings
from app.db import models
from app.utils.logger import get_logger


# список прокси для парсеров
proxies = [
    "83.220.171.231:12158:modeler_112BW6:wzDABWVp1qfM",
    "83.220.171.231:12159:modeler_lvtQMQ:d4tKgBklC9IH",
    "83.220.171.231:12160:modeler_mHIFb3:KgBbeRd8mENb",
    "83.220.171.231:12161:modeler_eUHOYz:4AHtE0ySGqsS",
    "83.220.171.231:12162:modeler_TMh2Ar:wMDtqE3mZFKk",
    "83.220.171.231:12165:modeler_eG3gYT:2ETp2gZpTfvM",
    "83.220.171.231:12166:modeler_Ua6YwT:nknBWaoRzgVl",
    "83.220.171.231:12167:modeler_7L1GfK:XZ8isCGavrlG",
    "83.220.171.231:12168:modeler_fK4dBX:GobRNv19T9Kn",
    "83.220.171.231:12169:modeler_Wbm9nc:mpRiR0nNH9Ze",
]

# стек используемых в данный момент прокси
used_proxies: list[str] = []


def get_random_proxy():
    """
    получить рандомный неиспользуемый прокси
    """
    if len(proxies) == len(used_proxies):
        logger.warning("Не хватило прокси для парсеров")
        return {}
    while True:
        proxy = random.choice(proxies)
        if proxy not in used_proxies:
            used_proxies.append(proxy)
            proxy_data = proxy.split(":")
            return {"proxy": f"http://{proxy_data[0]}:{proxy_data[1]}", "proxy_auth": (proxy_data[2], proxy_data[3])}


def find_proxy_by_url(url: str) -> str | None:
    """
    найти в used_proxies прокси по ссылке формата http://45.86.163.132:14632
    """
    proxy_sw = url.split("/")[-1]
    for proxy in used_proxies:
        if proxy.startswith(proxy_sw):
            return proxy


# датакласс для хранения в стеке хттп клиентов
@dataclass
class HttpSession:
    account_id: int
    client: requests.AsyncSession
    market: str
    created_at: datetime

    is_parser: bool = False
    init_data: str | None = None  # Telegram WebApp init data for authorization


# стек хттп клиентов
https_sessions: list[HttpSession] = []


# Ошибка на выполнении запроса
class RequestError(Exception):
    def __init__(self, result: str, *args):
        super().__init__(*args)
        self.result = result


class HTTPComposer:
    """
    Функционал для работы со стеком открытых соединений, так же настраивает парсеры для работы
    """

    log_level = logging.DEBUG

    market_name: str = "unknown"
    auth_expire: datetime = timedelta(minutes=30)

    def __init__(self, model: models.Account):
        self.model = model
        self.logger = HTTPComposer.generate_logger(self.model.id)

    @staticmethod
    def generate_logger(logger_id: str):
        # loguru не использует setLevel() - уровень настраивается глобально
        return get_logger(f"Account({logger_id})")

    @staticmethod
    async def get_parser(expired_time: timedelta, market: str) -> HttpSession | None:
        """
        Вернёт доступный HttpSession парсера
        """
        for s_ind, session in enumerate(https_sessions):
            if not session.is_parser:
                continue
            if session.market != market:
                continue

            # Проверка истечения срока - удаляем только если истек
            if session.created_at + expired_time < datetime.now():
                used_proxies.remove(find_proxy_by_url(session.client.proxies["all"]))
                await session.client.close()
                del https_sessions[s_ind]
                return None

            return session

        return None

    async def get_http_client(self, expired_time: timedelta, market: str) -> requests.AsyncSession | None:
        """
        Получение HTTP клиента с проверкой кэша
        """
        for s_ind, session in enumerate(https_sessions):
            if session.account_id != self.model.id:
                continue
            if session.market != market:
                continue

            if session.created_at + expired_time < datetime.now() - timedelta(minutes=1):
                if "all" in session.client.proxies:
                    used_proxies.remove(find_proxy_by_url(session.client.proxies["all"]))
                await session.client.close()
                del https_sessions[s_ind]
                return None

            return session.client

        return None

    def add_new_client(self, http_client: requests.AsyncSession, market: str, init_data: str | None = None):
        """
        Добавит новый клиент в стек
        """
        is_parser = False
        if self.model.name.startswith("PARSER") and self.model.user_id in settings.admins:
            is_parser = True

        cli = HttpSession(
            account_id=self.model.id,
            client=http_client,
            market=market,
            created_at=datetime.now(),
            is_parser=is_parser,
            init_data=init_data,
        )

        https_sessions.append(cli)

    def get_init_data_from_url(self, url: str) -> str:
        """
        Достаёт из ссылки авторизационные данные
        """
        parsed_url = urlparse(url)
        data = parse_qs(parsed_url.fragment)
        init_data = data["tgWebAppData"][0]
        return init_data

    async def init_base_http_client(
        self,
    ) -> requests.AsyncSession:
        """
        Инициализирует пустой http клиент
        """
        if self.model.name.startswith("PARSER") and self.model.user_id in settings.admins:
            http_client = requests.AsyncSession(**get_random_proxy())
        else:
            http_client = requests.AsyncSession()
        http_client.impersonate = "chrome"
        return http_client

    async def send_request(
        self,
        http_client: requests.AsyncSession,
        method: requests.session.HttpMethod,
        url: str,
        params: dict | list | tuple | None = None,
        data: dict[str, str] | list[tuple] | str | bytes | None = None,
        json: dict | list | None = None,
        headers: dict | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any] | list[Any]:
        """
        Отправка запроса на АПИ с обработкой ошибок и автоматическим retry.

        Args:
            max_retries: Максимальное количество попыток (по умолчанию 3)
        """
        from app.utils.retry import retry_async

        async def _make_request():
            res: requests.Response = await http_client.request(method, url, params, data, json, headers)

            if res.status_code < 200 or res.status_code >= 300:
                self.logger.error("Error request:")
                self.logger.error(f"{method}: {url}")
                self.logger.error(f"Sended: {params if params else ''} {data if data else ''} {json if json else ''}")
                self.logger.error(f"Result: {res.status_code}: {res.text}")
                raise RequestError(result=res.text)

            return res.json()

        # Выполняем запрос с retry механизмом
        return await retry_async(
            _make_request, max_attempts=max_retries, delay=1.0, backoff=2.0, exceptions=(RequestError, Exception)
        )

    async def get_ton_rates(self, http_client: requests.AsyncSession) -> dict[str, float]:
        """
        Получить цену за TON в долларах и рублях (с автоматическим retry)
        """
        data = await self.send_request(
            http_client,
            method="GET",
            url="https://tonapi.io/v2/rates?tokens=ton&currencies=ton,usd,rub",
            headers={"Authorization": "Bearer " + settings.tonconsole_api_key},
            max_retries=3,
        )
        return {
            "TON": data["rates"]["TON"]["prices"]["TON"],
            "USD": data["rates"]["TON"]["prices"]["USD"],
            "RUB": data["rates"]["TON"]["prices"]["RUB"],
        }
