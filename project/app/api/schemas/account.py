import datetime
import re

from pydantic import BaseModel, Field, field_validator


class AccountResponse(BaseModel):
    """Информация об аккаунте Telegram"""

    id: str = Field(min_length=1, max_length=255, description="ID аккаунта")
    user_id: int = Field(description="ID владельца аккаунта")
    phone: str | None = Field(None, description="Номер телефона")

    name: str | None = Field(None, min_length=1, max_length=255, description="Имя аккаунта")
    is_active: bool = Field(default=False, description="Активен ли аккаунт")
    telegram_id: int | None = Field(None, description="ID в Telegram")

    stars_balance: int = Field(default=0, ge=0, description="Баланс звёзд")
    is_premium: bool = Field(default=False, description="Премиум статус")

    created_at: datetime.datetime = Field(description="Дата создания")

    gift_setting_id: int | None = Field(None, description="ID настроек подарков")

    class Config:
        from_attributes = True


class ApproveRequest(BaseModel):
    """Запрос на подтверждение аккаунта"""

    id: str = Field(description="ID аккаунта")
    code: str = Field(min_length=4, max_length=10, description="Код подтверждения из Telegram")
    name: str = Field(min_length=1, max_length=255, description="Имя аккаунта")
    password: str | None = Field(None, min_length=1, max_length=255, description="Пароль 2FA (если установлен)")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Валидация кода подтверждения"""
        if not v.isdigit():
            raise ValueError("Код должен содержать только цифры")
        if len(v) < 4 or len(v) > 10:
            raise ValueError("Код должен содержать от 4 до 10 цифр")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Валидация имени аккаунта"""
        # Разрешаем любые символы, как в старом бэкенде
        if len(v) < 1 or len(v) > 255:
            raise ValueError("Имя должно содержать от 1 до 255 символов")
        return v

    class Config:
        # Разрешаем дополнительные поля (например mnemonic)
        extra = "ignore"
        json_schema_extra = {
            "example": {
                "id": "account_123",
                "code": "12345",
                "name": "my_account",
                "password": "my_2fa_password",
            }
        }


class AccountCreateRequest(BaseModel):
    """Запрос на создание аккаунта"""

    phone: str = Field(min_length=10, max_length=20, description="Номер телефона в международном формате")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Валидация номера телефона"""
        # Удаляем все символы кроме цифр и +
        cleaned = re.sub(r"[^\d+]", "", v)

        # Проверяем формат
        if not re.match(r"^\+?\d{10,15}$", cleaned):
            raise ValueError("Неверный формат телефона. Используйте международный формат, например: +79991234567")

        # Добавляем + если его нет
        if not cleaned.startswith("+"):
            cleaned = "+" + cleaned

        return cleaned

    class Config:
        json_schema_extra = {"example": {"phone": "+79991234567"}}
