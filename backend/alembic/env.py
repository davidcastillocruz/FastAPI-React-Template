import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# Registers every model in Base.metadata, so --autogenerate sees all the tables
import src.database.models  # noqa: F401
from src.core.settings import settings
from src.database.base import Base

# Config of alembic.ini
config = context.config

# Logging of the alembic commands, from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tables that --autogenerate compares with the database
target_metadata = Base.metadata


# Offline mode writes the SQL instead of running it: alembic upgrade head --sql
def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


# Same async driver as the app (asyncpg); the migrations run inside run_sync
# NullPool: one connection for the command, closed at the end
async def run_migrations_online() -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=pool.NullPool, hide_parameters=True)

    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
