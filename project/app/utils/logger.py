"""
Централизованная конфигурация логирования с использованием loguru.

Уровни логирования:
- DEBUG: Детальная информация для отладки (например, получение/освобождение блокировок)
- INFO: Общая информация о работе приложения (запуск задач, успешные операции)
- WARNING: Предупреждения о потенциальных проблемах (fallback режимы, повторные попытки)
- ERROR: Ошибки, которые не останавливают приложение
- CRITICAL: Критические ошибки, требующие немедленного внимания
"""

import json
import logging
import sys
from typing import Any

import requests
from loguru import logger

from app.configs import settings
from app.paths import resolve_logs_dir


# Удаляем дефолтный handler loguru
logger.remove()

# Определяем уровень логирования из переменной окружения
LOG_LEVEL = settings.log_level if hasattr(settings, "log_level") else "INFO"


def _to_level_no(level: Any) -> int:
    """Приводит уровень логирования к числовому значению."""

    try:
        return int(logging._checkLevel(level))
    except Exception:
        try:
            return logger.level(str(level)).no
        except Exception:
            return logger.level("INFO").no


_current_level_no = _to_level_no(LOG_LEVEL)


def _level_filter(record: dict[str, Any]) -> bool:
    """Общий фильтр для динамического изменения уровней хендлеров."""

    return record["level"].no >= _current_level_no

# Формат для консоли (читаемый)
CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# Формат для файлов (структурированный JSON для Loki)

# Консольный вывод (цветной, читаемый)
logger.add(
    sys.stdout,
    format=CONSOLE_FORMAT,
    level=LOG_LEVEL,
    filter=_level_filter,
    colorize=True,
    backtrace=True,
    diagnose=True,
)

# Файловые логи (ротация по дням)
LOG_DIR = resolve_logs_dir()
LOG_DIR.mkdir(parents=True, exist_ok=True)

def format_loki_record(record: dict) -> str:
    """Формирует JSON-строку для Loki с читаемым сообщением."""

    record["extra"]["loki_json"] = json.dumps(
        {
            "timestamp": record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "level": record["level"].name,
            "logger": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return "{extra[loki_json]}\n"


logger.add(
    LOG_DIR / "loki-app.log",
    format=format_loki_record,
    level=LOG_LEVEL,
    filter=_level_filter,
    rotation="00:00",
    retention=f"{settings.log_retention_days} days",
    compression="zip",
    encoding="utf-8",
)


_slack_webhook_url = getattr(settings, "slack_webhook_url", None)
_slack_missing_logged = False

"""
def send_slack_alert(record: dict[str, Any]) -> None:
    #Отправляет алерты уровня ERROR и выше в Slack.

    global _slack_missing_logged

    if not _slack_webhook_url:
        if not _slack_missing_logged:
            logger.warning("SLACK_WEBHOOK_URL не задан, алерты не будут отправляться")
            _slack_missing_logged = True
        return

    if record.get("level") is None or record["level"].no < logger.level("ERROR").no:
        return

    title = f":rotating_light: {record['level'].name} в {record['name']}"
    location = f"{record['file'].name}:{record['line']} — {record['function']}"
    message_text = str(record.get("message", ""))

    # чуть режем длину, чтобы не убиться об лимит Slack на блок
    max_len = 3000
    message_text = message_text[:max_len]

    # оборачиваем в код-блок
    code_block = f"```{message_text}```"

    payload = {
        "text": title,
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"{title}\n*Локация:* {location}"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Сообщение:*\n{code_block}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": record["time"].strftime("%Y-%m-%d %H:%M:%S"),
                    }
                ],
            },
        ],
    }

    def _fallback_payload() -> dict[str, Any]:
        #Упрощённое сообщение для случаев, когда blocks отклоняются.
        return {
            # fallback тоже можно оставить с код-блоком
            "text": f"{title}\nЛокация: {location}\n```{message_text}```",
        }

    try:
        response = requests.post(_slack_webhook_url, json=payload, timeout=5)
        if response.status_code == 400 and "invalid_blocks" in response.text.lower():
            response = requests.post(_slack_webhook_url, json=_fallback_payload(), timeout=5)

        if response.status_code != 200:
            logger.error(
                "Slack webhook вернул статус {status}: {body}",
                status=response.status_code,
                body=response.text,
            )
    except Exception:
        logger.exception("Не удалось отправить алерт в Slack")
"""

"""
def slack_alert_sink(message) -> None:
    #Sink для loguru, отправляющий сообщения в Slack.

    send_slack_alert(message.record)


logger.add(slack_alert_sink, level="ERROR", enqueue=True, filter=_level_filter)
"""

def _logger_set_level(level: Any) -> None:
    """Совместимость с API стандартного logging.Logger.setLevel."""

    global _current_level_no
    _current_level_no = _to_level_no(level)


# Добавляем совместимый метод на экземпляр loguru
logger.setLevel = _logger_set_level  # type: ignore[attr-defined]


def get_logger(name: str):
    """
    Получить logger с указанным именем.

    Args:
        name: Имя модуля (обычно __name__)

    Returns:
        Настроенный loguru logger

    Example:
        from app.utils.logger import get_logger

        logger = get_logger(__name__)
        logger.info("Application started")
    """
    return logger.bind(name=name)


# Интерцептор для перехвата стандартных логов Python


class InterceptHandler(logging.Handler):
    """
    Перехватывает стандартные логи Python и перенаправляет их в loguru.
    """

    def __init__(self, level=LOG_LEVEL):
        # Преобразуем строковый уровень в числовой для стандартного logging
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)
        super().__init__(level)
        self.level = level

    def emit(self, record):
        # Получаем соответствующий уровень Loguru
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Находим caller
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == __file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


# Экспортируем logger для использования в других модулях
__all__ = ["InterceptHandler", "get_logger", "logger"]