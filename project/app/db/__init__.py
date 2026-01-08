from .database import AsyncSession, SessionLocal
from .uow import UnitOfWork, get_uow


async def get_db():
    # Depends for db session
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()
