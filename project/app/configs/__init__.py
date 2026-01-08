import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Управление окружениями через переменную ENV
# ENV=test -> .env.test
# ENV=dev -> .env.dev
# ENV=prod -> .env (default)
env = os.getenv("ENV", "prod")

# Определить путь к .env файлу
if env == "test":
    env_file = Path(__file__).parent.parent.parent.parent / ".env.test"
elif env == "dev":
    env_file = Path(__file__).parent.parent.parent.parent / ".env.dev"
else:
    env_file = Path(__file__).parent.parent.parent.parent / ".env"

# Загрузить соответствующий .env файл
if env_file.exists():
    load_dotenv(env_file, override=True)
    print(f"✓ Loaded {env} environment from {env_file}")
else:
    print(f"⚠ Warning: {env_file} not found, using environment variables")
    load_dotenv()  # Fallback to default .env


class Settings(BaseSettings):
    database: str = Field(validation_alias="DATABASE")
    redis_url: str = "redis://redis:6379"
    domain: str

    ton_comission: float = 0.01
    market_comission: float = 1
    trade_comission: float = 2
    auction_comission: float = 5  # Комиссия аукционов в процентах

    bot_token: str
    bank_account: int
    parser_prefix: str = "PARSER"

    channel_username: str
    market_chat: str
    support_url: str
    admins: list[int] = []

    toncenter_api_key: str
    tonconsole_api_key: str
    output_wallet: str = "UQCYWG33knxOFzwmFnZKILNlTC5vtXQ4JV76LaQSkQq2xtKR"
    output_wallet_mnemonic: str

    logs_chat_id: int

    # Флаг для контроля инициализации Telegram сессий при запуске
    # При blue-green деплое нужно отключить для нового контейнера
    enable_telegram_init: bool = True

    log_retention_days: int = 7
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    slack_webhook_url: str | None = None

    # Ключ шифрования для чувствительных данных (Fernet key)
    encryption_key: str = Field(default="")

    # Fragment API settings
    fragment_api_key: str = Field(default="", validation_alias="FRAGMENT_API_KEY")
    stars_markup_percent: int = Field(default=10, validation_alias="STARS_MARKUP_PERCENT")

    model_config = SettingsConfigDict(env_file=None)

    def get_channel_url(self) -> str:
        return f"https://t.me/{self.channel_username}"

    def get_webhook_url(self) -> str:
        return f"https://api.{self.domain}/webhook"

    def get_webapp_url(self) -> str:
        return f"https://{self.domain}"

    def get_webapp_url_market(self) -> str:
        return f"https://{self.domain}/market"

    def get_gift_image(self, gift_id) -> str:
        return f"https://api.{self.domain}/media/{gift_id}.tgs"

    def get_banner(self) -> str:
        return f"https://api.{self.domain}/media/banner.png"

    def get_offer_url(self, offer_id) -> str:
        return f"https://{self.domain}/storage/?offer={offer_id}"


settings = Settings()