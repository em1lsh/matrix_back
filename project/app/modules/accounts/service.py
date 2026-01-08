"""Accounts модуль - Service"""

from app.utils.logger import get_logger

from .exceptions import AccountPermissionDeniedError


logger = get_logger(__name__)


class AccountService:
    def __init__(self, repository):
        self.repo = repository

    def validate_ownership(self, account, user_id: int):
        if account.user_id != user_id:
            raise AccountPermissionDeniedError(account.id)
