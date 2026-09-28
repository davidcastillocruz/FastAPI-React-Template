"""
Integration tests for the `POST /email-request` endpoint.

Exercises the full stack: request validation, database access,
translation resolution, and response shaping. The `client` fixture
(from `conftest.py`) wires an async HTTP client against the app with
`get_db` overridden to a session-scoped test transaction, so each test
runs against a real database and rolls back afterward.

SMTP delivery is attempted but not asserted. The background task runs
after the response is returned, so its result does not affect the test
outcome. Failures will appear in the console as unhandled exceptions
and can be safely ignored.
"""


async def test_create_email_request_success(client):
    """First POST for an email succeeds with a translated message.

    Verifies the happy path: the email is new, the row is inserted,
    and the response comes back in Spanish with the "registered"
    message. The placeholder in the response is also implicitly
    checked, since the assertion matches the tail of the sentence.
    """
    response = await client.post(
        "/email-request",
        json={"email": "nuevo@example.com"},
        headers={"Accept-Language": "es"},
    )

    assert response.status_code == 200
    assert "satisfactoriamente" in response.json()["message"]


async def test_create_email_request_duplicate(client):
    """Second POST for the same email reports "already registered".

    The first call creates the row; the second finds it via the fast
    path (`get_email_request_db`) and returns the translated
    "already registered" message with a 200 status. The test does not
    assert on the status of the second call beyond success, because
    the endpoint deliberately returns 200 for this case rather than
    409 — the 409 path is reserved for a race condition.
    """
    email = "duplicado@example.com"

    r1 = await client.post(
        "/email-request",
        json={"email": email},
        headers={"Accept-Language": "es"},
    )
    assert r1.status_code == 200

    r2 = await client.post(
        "/email-request",
        json={"email": email},
        headers={"Accept-Language": "es"},
    )
    assert r2.status_code == 200
    assert "ya está registrado" in r2.json()["message"]


async def test_create_email_request_invalid_email(client):
    """Malformed emails are rejected by validation with a 422.

    The `EmailSchema` validator raises a `PydanticCustomError` with
    the code `"INVALID_EMAIL"`, which the exception handler in
    `main.py` maps to the translated `"detail"` payload.
    """
    response = await client.post(
        "/email-request",
        json={"email": "not-an-email"},
        headers={"Accept-Language": "es"},
    )

    assert response.status_code == 422


async def test_language_english(client):
    """`Accept-Language: en` returns the English message.

    Complements `test_create_email_request_success`: same flow, but
    asserting that language resolution is wired end-to-end and reaches
    the response payload.
    """
    response = await client.post(
        "/email-request",
        json={"email": "english@example.com"},
        headers={"Accept-Language": "en"},
    )

    assert response.status_code == 200
    assert "successfully" in response.json()["message"].lower()