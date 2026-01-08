"""Trades модуль - Service"""

from app.utils.logger import get_logger

from .exceptions import TradePermissionDeniedError


logger = get_logger(__name__)


class TradeService:
    def __init__(self, repository):
        self.repo = repository

    def validate_ownership(self, trade, user_id: int):
        if trade.user_id != user_id:
            raise TradePermissionDeniedError(trade.id)
