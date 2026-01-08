from pathlib import Path


def _resolve_project_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_media_dir() -> Path:
    """Return the directory used for storing media files.

    В собранном Docker-образе проект располагается в ``/app`` и медиа-каталог
    лежит рядом с кодом. При работе из исходников структура сохраняется:
    исходный код находится в ``project/``, а ``media/`` располагается внутри
    него. Функция корректно определяет путь в обоих случаях и гарантирует
    существование директории.
    """
    project_root = _resolve_project_dir()
    media_dir = project_root / "media"

    media_dir.mkdir(parents=True, exist_ok=True)
    return media_dir


def resolve_logs_dir() -> Path:
    """Return the directory used for storing application logs."""
    project_root = _resolve_project_dir()
    logs_dir = project_root / "logs"

    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


__all__ = ["resolve_logs_dir", "resolve_media_dir"]
