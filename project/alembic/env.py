import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Engine, engine_from_config


# Загрузить правильное окружение ПЕРЕД импортом app
env = os.getenv("ENV", "prod")
if env == "test":
    env_file = Path(__file__).parent.parent.parent / ".env.test"
elif env == "dev":
    env_file = Path(__file__).parent.parent.parent / ".env.dev"
else:
    env_file = Path(__file__).parent.parent.parent / ".env"

if env_file.exists():
    load_dotenv(env_file, override=True)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config


def _ensure_sync_driver(database_url: str | None) -> str | None:
    if not database_url:
        return None

    replacements = {
        "+aiomysql": "+pymysql",
        "+asyncmy": "+pymysql",
        "+asyncpg": "+psycopg2",  # Use psycopg2 for migrations
        "+aiosqlite": "+pysqlite",
    }

    for async_driver, sync_driver in replacements.items():
        if async_driver in database_url:
            return database_url.replace(async_driver, sync_driver)

    return database_url


def _resolve_database_url() -> str | None:
    url = os.getenv("ALEMBIC_DATABASE")
    if url:
        return _ensure_sync_driver(url)

    url = os.getenv("DATABASE") or os.getenv("DATABASE")
    if url:
        return _ensure_sync_driver(url)

    try:
        from app.configs import settings  # type: ignore import-not-found

        candidate = getattr(settings, "database", None)
        if candidate:
            return _ensure_sync_driver(candidate)
    except Exception:
        # Fallback to value from configuration file if settings can't be loaded
        pass

    return _ensure_sync_driver(config.get_main_option("sqlalchemy.url"))


resolved_database_url = _resolve_database_url()
if resolved_database_url:
    config.set_main_option("sqlalchemy.url", resolved_database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from app.db.models import Base


target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def render_item(type_, obj, autogen_context):
    """Apply custom rendering for selected items."""

    if type_ == "type" and obj.__class__.__module__.startswith("sqlalchemy_utils."):
        autogen_context.imports.add(f"import {obj.__class__.__module__}")
        if hasattr(obj, "choices"):
            return f"{obj.__class__.__module__}.{obj.__class__.__name__}(choices={obj.choices})"
        else:
            return f"{obj.__class__.__module__}.{obj.__class__.__name__}()"

    # default rendering for other objects
    return False


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("Database URL is not configured for Alembic migrations")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_item=render_item,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # connectable = engine(
    #     config.get_section(config.config_ini_section, {}),
    #     prefix="sqlalchemy.",
    #     poolclass=pool.NullPool
    # )
    configuration = config.get_section(config.config_ini_section)
    if configuration is None:
        raise RuntimeError("Alembic configuration section is missing")

    connectable: Engine = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_item=render_item,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
