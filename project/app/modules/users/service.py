"""Users модуль - Service"""

from app.db.models import User
from app.utils.logger import get_logger

from .exceptions import TokenNotFoundError
from .repository import UserRepository


logger = get_logger(__name__)


class UserService:
    """Сервис пользователей"""

    def __init__(self, repository: UserRepository):
        self.repo = repository

    def validate_token(self, user: User) -> None:
        """Проверка наличия токена"""
        if not user.token:
            logger.error("User has no token", extra={"user_id": user.id})
            raise TokenNotFoundError()

    def convert_balance_to_ton(self, user: User) -> User:
        """Конвертировать баланс в TON"""
        user.market_balance = user.market_balance / 1e9
        return user
