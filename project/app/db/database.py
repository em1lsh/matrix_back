from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.configs import settings


# Оптимизация для высокой нагрузки (10k+ concurrent users)
engine = create_async_engine(
    settings.database,
    pool_recycle=3600 * 2,  # Переиспользование соединений каждые 2 часа
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_size=50,  # Базовый размер пула (было 10 по умолчанию)
    max_overflow=100,  # Дополнительные соединения при пиках нагрузки
    pool_timeout=30,  # Таймаут ожидания свободного соединения (сек)
    echo=False,  # Отключаем SQL логирование для производительности
)

SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Не делать expire объектов после commit (важно для тестов)
)
