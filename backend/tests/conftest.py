import uuid
from collections.abc import AsyncGenerator
from urllib.parse import urlsplit, urlunsplit

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.session import Base, get_db
from app.main import app
from app.models import (  # noqa: F401 -- register all models with Base.metadata
    chat,
    course,
    document,
    flashcard,
    generated_material,
    note,
    notebook,
    quiz,
    quiz_attempt,
    rag,
    user,
    weak_topic,
)

settings = get_settings()


def _test_database_url(base_url: str) -> str:
    """Derive an isolated `<db>_test` URL so tests never touch the dev database."""
    parts = urlsplit(base_url)
    test_path = parts.path.rstrip("/") + "_test"
    return urlunsplit((parts.scheme, parts.netloc, test_path, parts.query, parts.fragment))


TEST_DATABASE_URL = _test_database_url(settings.database_url)
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def _ensure_test_database_exists() -> None:
    from sqlalchemy import text

    parts = urlsplit(settings.database_url)
    test_db = parts.path.lstrip("/") + "_test"
    admin_url = urlunsplit((parts.scheme, parts.netloc, "/postgres", parts.query, parts.fragment))

    admin_engine = create_async_engine(admin_url, poolclass=NullPool, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": test_db}
        )
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{test_db}"'))
    await admin_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
async def _prepare_database() -> AsyncGenerator[None]:
    from sqlalchemy import text

    await _ensure_test_database_exists()
    async with test_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    async with TestSessionLocal() as session:
        yield session
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"
