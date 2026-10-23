from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.settings import settings

# Async engine using asyncpg
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    # Checks each connection before using it: one closed by PostgreSQL is replaced instead of failing the request
    pool_pre_ping=True,
    # Database errors don't include the query parameters (they would put emails in the logs).
    # The DETAIL line of a PostgreSQL error can still show a value ("Key (email)=(...) already exists"),
    # so a constraint error has to be caught (like the repeated email in the service), not logged with its traceback
    hide_parameters=True,
)

# Session factory, expire_on_commit=False keeps the objects readable after a commit
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


# FastAPI dependency: one session per request, closed (and rolled back if needed) when it ends
async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


# Database session of the request, in an endpoint: db: DbSession
DbSession = Annotated[AsyncSession, Depends(get_db)]
