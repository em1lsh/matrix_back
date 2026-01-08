import datetime
import typing

from pydantic import BaseModel, Field, field_validator


class AuthTokenResponse(BaseModel):
    """Ответ с токеном авторизации"""

    token: str = Field(min_length=32, max_length=512, description="JWT токен")

    class Config:
        json_schema_extra = {"example": {"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}}


class UserResponse(BaseModel):
    """Информация о пользователе"""

    id: int = Field(description="Telegram ID пользователя")
    language: str = Field(default="en", min_length=2, max_length=10, description="Код языка")

    payment_status: bool = Field(default=False, description="Статус оплаты")
    subscription_status: bool = Field(default=False, description="Статус подписки")
    market_balance: float = Field(default=0, ge=0, description="Баланс на маркете в TON")

    payment_date: datetime.datetime | None = Field(None, description="Дата последней оплаты")
    subscription_date: datetime.datetime | None = Field(None, description="Дата подписки")
    registration_date: datetime.datetime = Field(description="Дата регистрации")

    group: typing.Literal["member", "moderator", "admin", "owner"] = Field(
        default="member", description="Группа пользователя"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 123456789,
                "language": "en",
                "payment_status": True,
                "subscription_status": True,
                "market_balance": 150.5,
                "payment_date": "2025-12-01T12:00:00",
                "subscription_date": "2025-12-01T12:00:00",
                "registration_date": "2025-11-01T12:00:00",
                "group": "member",
            }
        }


class TopupResponse(BaseModel):
    """Информация о пополнении баланса"""

    amount: int = Field(ge=0, description="Сумма пополнения в nanotons")
    created_at: datetime.datetime = Field(description="Дата пополнения")

    class Config:
        from_attributes = True


class TopupsList(BaseModel):
    """Список пополнений пользователя"""

    topups: list[TopupResponse] = Field(default=[], description="Список пополнений")
    total: int = Field(ge=0, description="Общее количество пополнений")
    limit: int = Field(ge=1, description="Лимит элементов на странице")
    offset: int = Field(ge=0, description="Смещение")
    has_more: bool = Field(description="Есть ли ещё элементы")

    class Config:
        json_schema_extra = {
            "example": {
                "topups": [{"amount": 10000000000, "created_at": "2025-12-06T12:00:00"}],
                "total": 100,
                "limit": 20,
                "offset": 0,
                "has_more": True,
            }
        }


class WithdrawResponse(BaseModel):
    """Информация о выводе средств"""

    amount: int = Field(ge=0, description="Сумма вывода в nanotons")
    created_at: datetime.datetime = Field(description="Дата вывода")

    class Config:
        from_attributes = True


class WithdrawsList(BaseModel):
    """Список выводов пользователя"""

    withdraws: list[WithdrawResponse] = Field(default=[], description="Список выводов")
    total: int = Field(ge=0, description="Общее количество выводов")
    limit: int = Field(ge=1, description="Лимит элементов на странице")
    offset: int = Field(ge=0, description="Смещение")
    has_more: bool = Field(description="Есть ли ещё элементы")

    class Config:
        json_schema_extra = {
            "example": {
                "withdraws": [{"amount": 5000000000, "created_at": "2025-12-06T12:00:00"}],
                "total": 50,
                "limit": 20,
                "offset": 0,
                "has_more": True,
            }
        }


class TransactionResponse(BaseModel):
    """Транзакция (пополнение или вывод)"""

    type: typing.Literal["topup", "withdraw"] = Field(description="Тип транзакции")
    amount: float = Field(description="Сумма в TON")
    created_at: datetime.datetime = Field(description="Дата транзакции")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {"type": "topup", "amount": 10.5, "created_at": "2025-12-06T12:00:00"}
        }


class TransactionsList(BaseModel):
    """Список транзакций пользователя"""

    transactions: list[TransactionResponse] = Field(default=[], description="Список транзакций")
    total: int = Field(ge=0, description="Общее количество транзакций")
    limit: int = Field(ge=1, description="Лимит элементов на странице")
    offset: int = Field(ge=0, description="Смещение")
    has_more: bool = Field(description="Есть ли ещё элементы")

    class Config:
        json_schema_extra = {
            "example": {
                "transactions": [
                    {"type": "topup", "amount": 10.5, "created_at": "2025-12-06T12:00:00"},
                    {"type": "withdraw", "amount": 5.0, "created_at": "2025-12-05T10:00:00"},
                ],
                "total": 150,
                "limit": 20,
                "offset": 0,
                "has_more": True,
            }
        }


class PayResponse(BaseModel):
    """Данные для депозита"""

    amount: float = Field(gt=0, le=100000, description="Сумма пополнения в TON")
    wallet: str = Field(min_length=48, max_length=48, description="TON кошелёк для пополнения")
    memo: str = Field(min_length=1, max_length=32, description="Memo для идентификации платежа")

    @field_validator("wallet")
    @classmethod
    def validate_ton_wallet(cls, v: str) -> str:
        """Валидация TON адреса"""
        if not (v.startswith("EQ") or v.startswith("UQ")):
            raise ValueError("Неверный формат TON адреса (должен начинаться с EQ или UQ)")
        if len(v) != 48:
            raise ValueError("TON адрес должен содержать 48 символов")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 100.0,
                "wallet": "EQAbCdEfGhIjKlMnOpQrStUvWxYz0123456789AbCdEfGhIj",
                "memo": "USER123456",
            }
        }


class WithdrawRequest(BaseModel):
    """Запрос на вывод средств"""

    ton_amount: float = Field(gt=0, le=10000, description="Сумма вывода в TON", examples=[10.0, 50.0, 100.0])
    address: str = Field(min_length=48, max_length=48, description="TON адрес получателя")
    idempotency_key: str | None = Field(
        None, min_length=16, max_length=64, description="Ключ идемпотентности для предотвращения двойных выплат"
    )

    @field_validator("address")
    @classmethod
    def validate_ton_address(cls, v: str) -> str:
        """Валидация TON адреса"""
        if not (v.startswith("EQ") or v.startswith("UQ")):
            raise ValueError("Неверный формат TON адреса (должен начинаться с EQ или UQ)")
        if len(v) != 48:
            raise ValueError("TON адрес должен содержать 48 символов")
        return v

    @field_validator("ton_amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """Валидация суммы вывода"""
        if v < 0.1:
            raise ValueError("Минимальная сумма вывода 0.1 TON")
        return round(v, 2)

    class Config:
        json_schema_extra = {
            "example": {
                "ton_amount": 50.0,
                "address": "EQAbCdEfGhIjKlMnOpQrStUvWxYz0123456789AbCdEfGhIj",
                "idempotency_key": "unique-key-12345678",
            }
        }
