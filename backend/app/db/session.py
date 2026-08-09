from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

# Celery tasks (app/workers/document_tasks.py, notebook_tasks.py) each wrap their async work in
# a fresh asyncio.run() call, so every task runs on a new event loop. asyncpg connections are
# bound to the loop that created them; if a task reused `engine` above, the pool could hand a
# later task a connection opened on a now-closed loop from an earlier task, raising "Future
# attached to a different loop". NullPool opens a fresh connection per checkout and closes it on
# checkin, so no connection ever crosses a loop boundary -- same rationale as the NullPool
# `test_engine` in backend/tests/conftest.py, applied here for the same cross-loop reason rather
# than test isolation.
celery_engine = create_async_engine(settings.database_url, poolclass=NullPool)
celery_session_maker = async_sessionmaker(celery_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
