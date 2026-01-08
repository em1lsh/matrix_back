"""
Тесты для кастомных исключений приложения.
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

from app.exceptions import (
    AppException,
    AuctionAlreadyExistsError,
    AuthenticationError,
    BusinessLogicError,
    ChannelNotFoundError,
    CommitAfterRollbackError,
    DatabaseError,
    InsufficientBalanceError,
    InvalidOperationError,
    NFTNotFoundError,
    PermissionDeniedError,
    ResourceLockedError,
    TelegramAPIError,
)


class TestBaseExceptions:
    """Тесты базовых исключений"""

    def test_app_exception_basic(self):
        """Тест базового исключения"""
        exc = AppException("Test error")

        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.details == {}

    def test_app_exception_with_details(self):
        """Тест исключения с деталями"""
        exc = AppException("Test error", status_code=400, error_code="TEST_ERROR", details={"field": "value"})

        assert exc.status_code == 400
        assert exc.error_code == "TEST_ERROR"
        assert exc.details == {"field": "value"}


class TestResourceNotFoundErrors:
    """Тесты исключений "ресурс не найден" """

    def test_nft_not_found(self):
        """Тест NFTNotFoundError"""
        exc = NFTNotFoundError(123)

        assert exc.status_code == 400
        assert exc.error_code == "NFT_NOT_FOUND"
        assert exc.details["resource_type"] == "NFT"
        assert exc.details["resource_id"] == 123
        assert "NFT not found" in exc.message

    def test_channel_not_found(self):
        """Тест ChannelNotFoundError"""
        exc = ChannelNotFoundError(456)

        assert exc.status_code == 400
        assert exc.error_code == "CHANNEL_NOT_FOUND"
        assert exc.details["resource_id"] == 456


class TestResourceAlreadyExistsErrors:
    """Тесты исключений "ресурс уже существует" """

    def test_auction_already_exists(self):
        """Тест AuctionAlreadyExistsError"""
        exc = AuctionAlreadyExistsError(789)

        assert exc.status_code == 400
        assert exc.error_code == "AUCTION_ALREADY_EXISTS"
        assert exc.details["nft_id"] == 789
        assert "Auction already exists" in exc.message


class TestInsufficientBalanceError:
    """Тесты ошибки недостаточного баланса"""

    def test_insufficient_balance(self):
        """Тест InsufficientBalanceError"""
        exc = InsufficientBalanceError(required=1000, available=500)

        assert exc.status_code == 400
        assert exc.error_code == "INSUFFICIENT_BALANCE"
        assert exc.details["required"] == 1000
        assert exc.details["available"] == 500
        assert "1000" in exc.message
        assert "500" in exc.message


class TestInvalidOperationErrors:
    """Тесты недопустимых операций"""

    def test_invalid_operation(self):
        """Тест базового InvalidOperationError"""
        exc = InvalidOperationError("Cannot do this")

        assert exc.status_code == 400
        assert exc.error_code == "INVALID_OPERATION"
        assert exc.message == "Cannot do this"


class TestAuthenticationErrors:
    """Тесты ошибок аутентификации"""

    def test_authentication_error(self):
        """Тест AuthenticationError"""
        exc = AuthenticationError()

        assert exc.status_code == 401
        assert exc.error_code == "AUTHENTICATION_FAILED"
        assert "Authentication failed" in exc.message

    def test_authentication_error_custom_message(self):
        """Тест AuthenticationError с кастомным сообщением"""
        exc = AuthenticationError("Invalid token")

        assert exc.message == "Invalid token"


class TestPermissionErrors:
    """Тесты ошибок прав доступа"""

    def test_permission_denied(self):
        """Тест PermissionDeniedError"""
        exc = PermissionDeniedError()

        assert exc.status_code == 403
        assert exc.error_code == "PERMISSION_DENIED"

    def test_permission_denied_with_resource(self):
        """Тест PermissionDeniedError с указанием ресурса"""
        exc = PermissionDeniedError("Cannot access", resource="channel:123")

        assert exc.details["resource"] == "channel:123"


class TestConflictErrors:
    """Тесты конфликтов ресурсов"""

    def test_resource_locked(self):
        """Тест ResourceLockedError"""
        exc = ResourceLockedError("NFT", 123)

        assert exc.status_code == 409
        assert exc.error_code == "RESOURCE_CONFLICT"
        assert exc.details["resource_type"] == "NFT"
        assert exc.details["resource_id"] == 123


class TestExternalServiceErrors:
    """Тесты ошибок внешних сервисов"""

    def test_telegram_api_error(self):
        """Тест TelegramAPIError"""
        exc = TelegramAPIError("API timeout")

        assert exc.status_code == 502
        assert exc.error_code == "TELEGRAM_ERROR"
        assert "Telegram error" in exc.message
        assert "API timeout" in exc.message


class TestDatabaseErrors:
    """Тесты ошибок БД"""

    def test_database_error(self):
        """Тест DatabaseError"""
        exc = DatabaseError("Connection lost")

        assert exc.status_code == 500
        assert exc.error_code == "DATABASE_ERROR"
        assert exc.message == "Connection lost"

    def test_commit_after_rollback_error(self):
        """Тест CommitAfterRollbackError"""
        exc = CommitAfterRollbackError()

        assert exc.status_code == 500
        assert "Cannot commit after rollback" in exc.message


class TestExceptionInheritance:
    """Тесты иерархии исключений"""

    def test_all_inherit_from_app_exception(self):
        """Все кастомные исключения наследуются от AppException"""
        exceptions = [
            NFTNotFoundError(1),
            InsufficientBalanceError(100, 50),
            AuthenticationError(),
            PermissionDeniedError(),
            ResourceLockedError("test", 1),
            TelegramAPIError("test"),
            DatabaseError("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, AppException)
            assert isinstance(exc, Exception)

    def test_business_logic_errors_have_400_status(self):
        """Все бизнес-ошибки имеют статус 400"""
        exceptions = [
            NFTNotFoundError(1),
            ChannelNotFoundError(1),
            InsufficientBalanceError(100, 50),
            InvalidOperationError("test"),
            AuctionAlreadyExistsError(1),
        ]

        for exc in exceptions:
            assert exc.status_code == 400
            assert isinstance(exc, BusinessLogicError)
