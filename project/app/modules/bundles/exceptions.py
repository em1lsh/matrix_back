from app.shared.exceptions import AppException


class BundleNotFoundError(AppException):
    def __init__(self, bundle_id: int):
        super().__init__(
            f"Bundle {bundle_id} not found", status_code=404, error_code="BUNDLE_NOT_FOUND", details={"bundle_id": bundle_id}
        )


class BundlePermissionDeniedError(AppException):
    def __init__(self, bundle_id: int):
        super().__init__(
            f"Permission denied for bundle {bundle_id}",
            status_code=403,
            error_code="BUNDLE_PERMISSION_DENIED",
            details={"bundle_id": bundle_id},
        )


class BundleNotActiveError(AppException):
    def __init__(self, bundle_id: int):
        super().__init__(
            f"Bundle {bundle_id} is not active",
            status_code=400,
            error_code="BUNDLE_NOT_ACTIVE",
            details={"bundle_id": bundle_id},
        )


class InvalidBundleItemsError(AppException):
    def __init__(self, message: str, nft_ids: list[int]):
        super().__init__(
            message,
            status_code=400,
            error_code="INVALID_BUNDLE_ITEMS",
            details={"nft_ids": nft_ids},
        )