"""Aggregator модуль - Service"""

from urllib.parse import urljoin

import aiohttp
from pydantic import ValidationError

from app.utils.logger import get_logger

from .exceptions import (
    AggregatorAPIError,
    AggregatorRateLimitError,
    AggregatorUnauthorizedError,
)
from .schemas import AggregatorFilter, AggregatorResponse

logger = get_logger(__name__)


class AggregatorService:
    """HTTP клиент для внешнего агрегатора"""

    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout

    async def fetch(self, payload: AggregatorFilter, page: int) -> AggregatorResponse:
        """Запросить данные у внешнего агрегатора"""
        if not self.api_key:
            raise AggregatorUnauthorizedError("Missing API key for aggregator")

        url = urljoin(self.base_url, "/api/aggregator")
        headers = {
            "accept": "application/json",
            "x-api-key": self.api_key,
            "content-type": "application/json",
        }
        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            try:
                async with session.post(
                    url,
                    params={"page": page},
                    json=payload.model_dump(mode="json", exclude_none=True),
                ) as response:
                    if response.status in {401, 403}:
                        raise AggregatorUnauthorizedError("Aggregator API unauthorized")
                    if response.status == 429:
                        raise AggregatorRateLimitError("Aggregator API rate limit exceeded")
                    if response.status >= 400:
                        error_text = await response.text()
                        raise AggregatorAPIError(
                            f"Aggregator API error {response.status}: {error_text}"
                        )
                    data = await response.json()
                    try:
                        return AggregatorResponse.model_validate(data)
                    except ValidationError as exc:
                        raise AggregatorAPIError(f"Aggregator response invalid: {exc}") from exc
            except aiohttp.ClientError as exc:
                logger.warning("Aggregator API request failed: %s", exc)
                raise AggregatorAPIError(f"Aggregator API request failed: {exc}") from exc
