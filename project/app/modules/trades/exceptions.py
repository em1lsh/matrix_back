"""Trades модуль - Исключения"""

from app.shared.exceptions import AppException


class TradeNotFoundError(AppException):
    """Трейд не найден"""

    def __init__(self, trade_id: int):
        super().__init__(
            f"Trade {trade_id} not found", status_code=404, error_code="TRADE_NOT_FOUND", details={"trade_id": trade_id}
        )


class TradePermissionDeniedError(AppException):
    """Нет прав на трейд"""

    def __init__(self, trade_id: int):
        super().__init__(
            f"Permission denied for trade {trade_id}",
            status_code=403,
            error_code="TRADE_PERMISSION_DENIED",
            details={"trade_id": trade_id},
        )


class ProposalNotFoundError(AppException):
    """Предложение обмена не найдено"""

    def __init__(self, proposal_id: int):
        super().__init__(
            f"Proposal {proposal_id} not found",
            status_code=404,
            error_code="PROPOSAL_NOT_FOUND",
            details={"proposal_id": proposal_id},
        )


class TradeRequirementsNotMetError(AppException):
    """Предложение не соответствует требованиям трейда"""

    def __init__(self, trade_id: int):
        super().__init__(
            f"Proposal does not meet trade {trade_id} requirements",
            status_code=400,
            error_code="TRADE_REQUIREMENTS_NOT_MET",
            details={"trade_id": trade_id},
        )


class ProposalAlreadyExistsError(AppException):
    """Пользователь уже создал предложение на этот трейд"""

    def __init__(self, trade_id: int):
        super().__init__(
            f"Proposal already exists for trade {trade_id}",
            status_code=400,
            error_code="PROPOSAL_ALREADY_EXISTS",
            details={"trade_id": trade_id},
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


class NFTsNotOwnedError(AppException):
    """NFT не принадлежат пользователю"""

    def __init__(self, nft_ids: list[int]):
        super().__init__(
            f"NFTs {nft_ids} not owned by user",
            status_code=400,
            error_code="NFTS_NOT_OWNED",
            details={"nft_ids": nft_ids},
        )


__all__ = [
    "AppException",
    "InsufficientBalanceError",
    "NFTsNotOwnedError",
    "ProposalAlreadyExistsError",
    "ProposalNotFoundError",
    "TradeNotFoundError",
    "TradePermissionDeniedError",
    "TradeRequirementsNotMetError",
]
