"""
Скрипт для пересоздания тестовой базы данных
"""

import os
import sys
from pathlib import Path


# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# Загружаем тестовое окружение
env_path = Path(__file__).parent.parent / ".env.test"
load_dotenv(env_path)

# Получаем параметры подключения
db_host = os.getenv("POSTGRES_HOST", "localhost")
db_port = os.getenv("POSTGRES_PORT", "5432")
db_user = os.getenv("POSTGRES_USER", "postgres")
db_password = os.getenv("POSTGRES_PASSWORD", "postgres")
db_name = os.getenv("POSTGRES_DB", "loadtest_db")

# Подключаемся к postgres для пересоздания базы
postgres_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/postgres"
engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")

print(f"Пересоздаём базу данных {db_name}...")

with engine.connect() as conn:
    # Отключаем все соединения
    conn.execute(
        text(f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{db_name}'
        AND pid <> pg_backend_pid();
    """)
    )

    # Удаляем базу
    conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
    print(f"✓ База {db_name} удалена")

    # Создаём базу заново
    conn.execute(text(f"CREATE DATABASE {db_name}"))
    print(f"✓ База {db_name} создана")

print("\n✓ Готово! Теперь запустите: poetry run alembic upgrade head")
