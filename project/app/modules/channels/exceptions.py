"""Channels модуль - Исключения"""

from app.shared.exceptions import AppException


class ChannelNotFoundError(AppException):
    """Канал не найден"""

    def __init__(self, channel_id: int):
        super().__init__(
            f"Channel {channel_id} not found",
            status_code=404,
            error_code="CHANNEL_NOT_FOUND",
            details={"channel_id": channel_id},
        )


class ChannelPermissionDeniedError(AppException):
    """Нет прав на канал"""

    def __init__(self, channel_id: int):
        super().__init__(
            f"Permission denied for channel {channel_id}",
            status_code=403,
            error_code="CHANNEL_PERMISSION_DENIED",
            details={"channel_id": channel_id},
        )


class ChannelHasNoGiftsError(AppException):
    """Канал не имеет подарков"""

    def __init__(self, channel_id: int):
        super().__init__(
            f"Channel {channel_id} does not have gifts",
            status_code=400,
            error_code="CHANNEL_HAS_NO_GIFTS",
            details={"channel_id": channel_id},
        )


class InsufficientBalanceError(AppException):
    """Недостаточно средств"""

    def __init__(self, required: int, available: int):
        super().__init__(
            f"Insufficient balance. Required: {required}, Available: {available}",
            status_code=400,
            error_code="INSUFFICIENT_BALANCE",
            details={"required": required, "available": available},
        )


class ChannelGiftsModifiedError(AppException):
    """Подарки канала были изменены"""

    def __init__(self, channel_id: int):
        super().__init__(
            f"Channel {channel_id} gifts have been modified since the last check",
            status_code=400,
            error_code="CHANNEL_GIFTS_MODIFIED",
            details={"channel_id": channel_id},
        )


class ReceiverNotSubscribedError(AppException):
    """Получатель не подписан на канал"""

    def __init__(self, receiver: str):
        super().__init__(
            f"Receiver {receiver} not subscribed to channel",
            status_code=400,
            error_code="RECEIVER_NOT_SUBSCRIBED",
            details={"receiver": receiver},
        )


class ChannelTransferError(AppException):
    """Ошибка передачи канала"""

    def __init__(self, channel_id: int, reason: str = "Unexpected error"):
        super().__init__(
            f"Failed to transfer channel {channel_id}: {reason}",
            status_code=500,
            error_code="CHANNEL_TRANSFER_ERROR",
            details={"channel_id": channel_id, "reason": reason},
        )


__all__ = [
    "AppException",
    "ChannelGiftsModifiedError",
    "ChannelHasNoGiftsError",
    "ChannelNotFoundError",
    "ChannelPermissionDeniedError",
    "ChannelTransferError",
    "InsufficientBalanceError",
    "ReceiverNotSubscribedError",
]
