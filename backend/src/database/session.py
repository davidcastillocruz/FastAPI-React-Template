"""
Async database engine and session factory.

Creates a single `AsyncEngine` bound to `config.DATABASE_URL_ASYNC` and
an `AsyncSessionLocal` factory used to produce per-request sessions.
The engine is created once at import time and reused for the lifetime
of the process; sessions are short-lived and tied to a request.

`get_db` is the FastAPI dependency that provides a session to route
handlers and services. It must be used with `Depends(get_db)` so that
FastAPI closes the session at the end of the request.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.core import config

# Engine settings rationale:
# - `pool_pre_ping=True` verifies connections are alive before use,
#   protecting against idle timeouts (e.g. from Postgres or a proxy).
# - `pool_recycle=300` recycles connections after 5 minutes, so any
#   connection the server closed silently is not reused.
# - `pool_size=10` + `max_overflow=20` allow up to 30 concurrent
#   connections under load before requests start waiting.
engine = create_async_engine(
    config.DATABASE_URL_ASYNC,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
)

# `expire_on_commit=False` keeps attributes accessible after commit
# without triggering a refresh query. Useful when returning model
# instances to the response layer right after a write.
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """FastAPI dependency that yields a database session.

    The session is opened when the request starts and closed when it
    ends. Use it as:

        db: AsyncSession = Depends(get_db)

    Yields:
        An `AsyncSession` bound to the shared engine.
    """
    async with AsyncSessionLocal() as session:
        yield session