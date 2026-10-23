import pytest
from fastapi import BackgroundTasks
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.database.session import DbSession, engine
from src.main import app


# The background tasks run after the response: a slow mail server can't keep a connection of the pool busy
async def test_a_background_task_holds_no_connection(client):
    connections = []

    def task() -> None:
        connections.append(engine.pool.checkedout())  # pyright: ignore[reportAttributeAccessIssue]

    # Reads and leaves its transaction open: only closing the session gives the connection back
    async def read(db: DbSession, background_tasks: BackgroundTasks) -> None:
        await db.execute(text("SELECT 1"))
        background_tasks.add_task(task)

    app.add_api_route("/test-read", read, methods=["GET"])
    await client.get("/test-read")
    app.router.routes = [r for r in app.router.routes if getattr(r, "path", "") != "/test-read"]
    # The docs were generated with this route: the next visit generates them again
    app.openapi_schema = None

    assert connections == [0]


async def test_database_errors_hide_the_parameters(client):
    insert = text("INSERT INTO email_requests (email) VALUES (:email)")
    async with engine.begin() as connection:
        await connection.execute(insert, {"email": "ana@test.dev"})

    with pytest.raises(IntegrityError) as error:
        async with engine.begin() as connection:
            await connection.execute(insert, {"email": "ana@test.dev"})

    assert "ana@test.dev" not in str(error.value)
