"""
Pytest fixtures and session-scoped setup for the backend test suite.

Responsibilities:

- **Docker**: brings up a throwaway Postgres container before the
  session starts and tears it down when it ends.
- **Environment**: loads `.env.test` *before* importing the app, so the
  app config picks up the test database URL.
- **Database schema**: applies Alembic migrations once per session and
  resets the schema on both ends.
- **Translations**: loads the translations JSON into memory, mimicking
  the app's `lifespan` startup.
- **HTTP client**: exposes an `AsyncClient` with `get_db` overridden to
  the test session so tests share a single transaction.

Import order matters in this file: `load_dotenv` must run before any
`src.*` import, otherwise `config.py` would read the development `.env`
instead of `.env.test`.
"""

import asyncio
import os
import subprocess
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
COMPOSE_FILE = BACKEND_DIR / "docker-compose.test.yml"


# ---------------------------------------------------------------------------
# Environment (must run before importing the app)
# ---------------------------------------------------------------------------
load_dotenv(BACKEND_DIR / ".env.test", override=True)

# Imports below must come after `load_dotenv` so `config` picks up the
# test environment. `Base` is imported for its side effect: it forces
# Alembic to see every model before running migrations.
from src.core import language_data  # noqa: E402
from src.database.base import Base  # noqa: E402, F401
from src.database.session import get_db  # noqa: E402
from src.main import app  # noqa: E402

TEST_DATABASE_URL = os.environ["DATABASE_URL_ASYNC"]

# Engine and session factory scoped to the test session. Reused across
# all async tests via the `db_session` fixture.
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# ---------------------------------------------------------------------------
# Docker: Postgres container lifecycle
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def docker_compose():
    """Bring up the test Postgres container and tear it down at the end.

    Fails fast with a clear message if Docker is not running, rather
    than letting the first test fail with a cryptic connection error.
    """
    # Fail fast if Docker is not available.
    check = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True,
    )
    if check.returncode != 0:
        pytest.exit(
            "Docker is not running. Start Docker Desktop and try again.",
            returncode=1,
        )

    # Clean up anything left over from a previous interrupted run.
    subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "down", "-v"],
        capture_output=True,
        check=False,
    )

    # Start the container and wait until the healthcheck passes.
    subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "up", "-d", "--wait"],
        check=True,
    )

    yield

    # Tear down at the end of the session.
    subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "down", "-v"],
        check=False,
    )


# ---------------------------------------------------------------------------
# App state: translations in memory
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def load_translations():
    """Load the translations JSON into memory.

    Mimics the app's `lifespan` startup. Without this, calls to
    `get_response` / `get_exception` would raise `KeyError` because the
    in-memory store would be empty.
    """
    language_data.load()


# ---------------------------------------------------------------------------
# Database: schema setup via Alembic
# ---------------------------------------------------------------------------
def _alembic_config() -> Config:
    """Build an Alembic config pointing at the test database.

    `script_location` is read from `alembic.ini` so the migrations
    directory is not duplicated here.
    """
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return cfg


@pytest.fixture(scope="session")
def setup_database(docker_compose, load_translations):
    """Apply Alembic migrations once for the whole session.

    This fixture is intentionally **synchronous**: Alembic's `env.py`
    calls `asyncio.run()` internally, which cannot be nested inside
    pytest-asyncio's event loop. By keeping the fixture sync, Alembic
    runs its own loop without conflict.
    """
    async def _reset_schema() -> None:
        # Each call creates and disposes its own engine, so it is safe
        # to run under `asyncio.run()` outside the test session's loop.
        eng = create_async_engine(TEST_DATABASE_URL)
        async with eng.begin() as conn:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
        await eng.dispose()

    asyncio.run(_reset_schema())
    command.upgrade(_alembic_config(), "head")

    yield

    asyncio.run(_reset_schema())


# ---------------------------------------------------------------------------
# Per-test fixtures
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def db_session(setup_database):
    """Yield an async session, rolled back after each test.

    The rollback ensures tests do not leak state into each other. The
    session shares the connection pool with the app, so endpoints
    see exactly what the test wrote.
    """
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """HTTP client with `get_db` overridden to the test session.

    The override replaces the app's real database dependency with the
    test session, so endpoints run against the same transaction the
    test can inspect and roll back.
    """
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()