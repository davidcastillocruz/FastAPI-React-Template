import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.core.limiter import limiter
from src.database.session import engine
from src.main import app
from src.modules.demo.repositories import email_request_repository
from src.modules.demo.services.email_request_service import PAGE_SIZE


async def create(client, email: str, **kwargs):
    return await client.post("/email-requests", json={"email": email}, **kwargs)


async def test_create_saves_and_sends_the_email(client, sent_emails):
    response = await create(client, "Ana@Test.dev")

    assert response.status_code == 201
    assert response.json() == {"message": "Done! Check your inbox in a few seconds"}
    assert response.headers["X-Request-ID"]
    # Saved and sent in lowercase
    assert sent_emails[0][1] == ["ana@test.dev"]
    assert sent_emails[0][0] == "Your test email"
    assert [row["email"] for row in (await client.get("/email-requests")).json()] == ["ana@test.dev"]


async def test_create_in_spanish(client, sent_emails):
    response = await create(client, "ana@test.dev", params={"lang": "es"})

    assert response.json() == {"message": "¡Hecho! Revisa tu bandeja de entrada en unos segundos"}
    assert sent_emails[0][0] == "Tu email de prueba"


async def test_create_twice_is_a_conflict(client, sent_emails):
    # The first one in uppercase too: both are saved and looked up in lowercase
    await create(client, "Ana@test.dev")
    response = await create(client, "ANA@test.dev")

    assert response.status_code == 409
    assert response.json() == {"detail": "This email has already asked for a test email"}
    # Only the first one sends an email
    assert len(sent_emails) == 1
    spanish = await create(client, "ana@test.dev", params={"lang": "es"})
    assert spanish.json() == {"detail": "Este email ya ha pedido un email de prueba"}


async def test_create_with_an_invalid_email(client, sent_emails):
    response = await create(client, "not-an-email", headers={"Accept-Language": "es-ES,es;q=0.9"})

    assert response.status_code == 422
    assert response.json() == {"detail": "Revisa estos campos: email"}
    assert sent_emails == []


async def test_create_without_body(client):
    response = await client.post("/email-requests")

    assert response.status_code == 422
    assert response.json() == {"detail": "Check these fields: body"}


async def test_create_is_rate_limited(client):
    responses = [await create(client, f"user{i}@test.dev", params={"lang": "es"}) for i in range(6)]

    assert [response.status_code for response in responses] == [201] * 5 + [429]
    assert responses[-1].json() == {"detail": "Demasiadas peticiones, espera un momento y vuelve a intentarlo"}


async def test_rate_limit_is_per_client_ip(client):
    for i in range(6):
        await create(client, f"user{i}@test.dev")

    # Another IP still has its 5 requests
    transport = ASGITransport(app=app, client=("10.0.0.2", 123))
    async with AsyncClient(transport=transport, base_url="http://test") as other_client:
        response = await create(other_client, "other@test.dev")

    assert response.status_code == 201


async def test_create_at_the_same_time_is_a_conflict(client, monkeypatch, sent_emails):
    # Two requests that both pass the check before either saves: the unique constraint stops the second one
    async def not_found_yet(db, email):
        return None

    monkeypatch.setattr(email_request_repository, "get_email_request_by_email", not_found_yet)
    await create(client, "ana@test.dev")
    response = await create(client, "ana@test.dev")

    assert response.status_code == 409
    assert response.json() == {"detail": "This email has already asked for a test email"}
    assert len(sent_emails) == 1


async def test_database_errors_hide_the_parameters(client):
    insert = text("INSERT INTO email_requests (email) VALUES (:email)")
    async with engine.begin() as connection:
        await connection.execute(insert, {"email": "ana@test.dev"})

    with pytest.raises(IntegrityError) as error:
        async with engine.begin() as connection:
            await connection.execute(insert, {"email": "ana@test.dev"})

    assert "ana@test.dev" not in str(error.value)


async def test_list_is_empty(client):
    response = await client.get("/email-requests")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_pages_newest_first(client):
    # 12 requests, without hitting the rate limit
    for i in range(12):
        await create(client, f"user{i:02}@test.dev")
        limiter.reset()

    page_1 = (await client.get("/email-requests")).json()
    page_2 = (await client.get("/email-requests", params={"page": 2})).json()
    page_3 = (await client.get("/email-requests", params={"page": 3})).json()

    assert len(page_1) == PAGE_SIZE and len(page_2) == 2 and page_3 == []
    # Newest first, no row repeated or skipped
    emails = [row["email"] for row in page_1 + page_2]
    assert emails == [f"user{i:02}@test.dev" for i in reversed(range(12))]
    assert set(page_1[0]) == {"id", "email", "created_at"}


async def test_list_breaks_ties_by_id(client):
    # Same created_at for every row: the newest id goes first, so the pages never repeat or skip a row
    async with engine.begin() as connection:
        await connection.execute(
            text("INSERT INTO email_requests (email, created_at) VALUES (:email, '2026-01-01T00:00:00Z')"),
            [{"email": f"same{i}@test.dev"} for i in range(3)],
        )

    rows = (await client.get("/email-requests")).json()

    assert [row["id"] for row in rows] == [3, 2, 1]


async def test_list_with_an_invalid_page(client):
    for page in ("0", "-1", "abc", "100001"):
        response = await client.get("/email-requests", params={"page": page, "lang": "es"})
        assert response.status_code == 422
        assert response.json() == {"detail": "Revisa estos campos: page"}
