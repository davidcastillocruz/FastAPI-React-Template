import os

# Before importing the app: the tests use their own database, keep the rate limit counters in memory
# and don't depend on how each developer customized .env.api (the assertions expect these values)
os.environ["POSTGRES_DB"] = "app_test"
os.environ["RATE_LIMIT_STORAGE_URI"] = "memory://"
os.environ["APP_MODE"] = "development"
os.environ["MAIN_LANGUAGE"] = "en"
os.environ["AVAILABLE_LANGUAGES"] = "en,es"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.core.languages import setup_language_system
from src.core.limiter import limiter
from src.core.settings import settings
from src.database.base import Base
from src.database.session import engine
from src.main import app
from src.modules.demo.services import email_request_service


# The lifespan doesn't run with the test client, the languages are loaded here once
@pytest.fixture(scope="session", autouse=True)
def languages():
    setup_language_system()


# Creates the test database once, with the tables of the models (CI checks that the migrations match them).
# Only the tests that call the API need it (through client), the unit tests run without PostgreSQL
@pytest.fixture(scope="session")
async def database():
    admin_url = settings.DATABASE_URL.set(database="postgres")
    admin = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as connection:
        exists = await connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": settings.POSTGRES_DB},
        )
        if not exists:
            await connection.execute(text(f'CREATE DATABASE "{settings.POSTGRES_DB}"'))
    await admin.dispose()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


# Every API test starts with empty tables and fresh rate limit counters
@pytest.fixture
async def clean_state(database):
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    limiter.reset()


# Emails are recorded instead of sent: (subject, recipients, body)
@pytest.fixture(autouse=True)
def sent_emails(monkeypatch) -> list[tuple]:
    sent = []

    async def fake_send_email(subject: str, recipients: list[str], body: str) -> None:
        sent.append((subject, recipients, body))

    monkeypatch.setattr(email_request_service, "send_email", fake_send_email)
    return sent


# Calls the app directly, without a server
@pytest.fixture
async def client(clean_state):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
