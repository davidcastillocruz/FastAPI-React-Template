"""
Unit tests for `language_manager.get_language`.

These tests exercise the language resolution logic in isolation, without
touching the app, the database, or any FastAPI middleware. Requests are
built with a hand-crafted Starlette `Request` object that only carries
the headers (and optional cookie) needed for the test.

Assumptions:

- `PROJECT_MAIN_LANGUAGE` is `"en"` in `.env.test`, which is why the
  fallback assertions expect `"en"`. Update the fixtures in
  `conftest.py` if the default changes.
- `PROJECT_SUPPORTED_LANGUAGES` includes at least `"en"` and `"es"`.
"""

from starlette.requests import Request

from src.core.language_manager import get_language


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fake_request(
    accept_language: str | None = None,
    cookie: str | None = None,
) -> Request:
    """Build a minimal Starlette `Request` for testing `get_language`.

    Starlette reads cookies from the `Cookie` header, not from a
    `scope["cookies"]` entry, so the cookie is encoded as a header here.

    Args:
        accept_language: Value for the `Accept-Language` header. If
            `None`, the header is omitted.
        cookie: Value for the `language` cookie. If `None`, the cookie
            is omitted.

    Returns:
        A `Request` with only the headers needed by `get_language`.
    """
    headers = []
    if accept_language is not None:
        headers.append((b"accept-language", accept_language.encode()))
    if cookie is not None:
        headers.append((b"cookie", f"language={cookie}".encode()))

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
    }
    return Request(scope)


# ---------------------------------------------------------------------------
# Header: basic matching
# ---------------------------------------------------------------------------
def test_exact_match():
    """A single supported language matches exactly."""
    assert get_language(_fake_request("es")) == "es"


def test_regional_variant():
    """`"es-ES"` is reduced to its base form, `"es"`."""
    assert get_language(_fake_request("es-ES")) == "es"


def test_fallback_to_default():
    """An unsupported language falls back to the default."""
    assert get_language(_fake_request("fr")) == "en"


def test_empty_header():
    """An empty `Accept-Language` value falls back to the default."""
    assert get_language(_fake_request("")) == "en"


def test_no_header():
    """A missing `Accept-Language` header falls back to the default."""
    assert get_language(_fake_request(None)) == "en"


def test_first_supported_wins():
    """The first supported language in the header is returned.

    `fr` is not supported, `en` is first supported, so it wins over
    `es` even though both have a `q` value.
    """
    assert get_language(_fake_request("fr,en;q=0.9,es;q=0.8")) == "en"


# ---------------------------------------------------------------------------
# Header: q parameter and case
# ---------------------------------------------------------------------------
def test_header_single_with_q():
    """A single language with a `q` parameter still matches.

    Guards against the historical bug where `"en;q=0.8"` was rejected
    because the `q` suffix was not stripped.
    """
    assert get_language(_fake_request("en;q=0.8")) == "en"


def test_header_regional_with_q():
    """A regional variant with a `q` parameter reduces to its base."""
    assert get_language(_fake_request("es-MX;q=0.9")) == "es"


def test_header_mixed_case():
    """Language codes are matched case-insensitively."""
    assert get_language(_fake_request("EN")) == "en"


# ---------------------------------------------------------------------------
# Cookie
# ---------------------------------------------------------------------------
def test_cookie_only():
    """A cookie alone is enough to pick a language."""
    assert get_language(_fake_request(cookie="es")) == "es"


def test_cookie_wins_over_header():
    """The cookie takes precedence over `Accept-Language`."""
    req = _fake_request(accept_language="en", cookie="es")
    assert get_language(req) == "es"


def test_cookie_regional_variant():
    """A regional cookie value is reduced to its base form."""
    assert get_language(_fake_request(cookie="es-MX")) == "es"


def test_cookie_uppercase():
    """Cookie values are matched case-insensitively."""
    assert get_language(_fake_request(cookie="ES")) == "es"


def test_cookie_with_spaces():
    """Whitespace around a cookie value is stripped before matching."""
    assert get_language(_fake_request(cookie="  es  ")) == "es"


def test_cookie_invalid_falls_back_to_header():
    """An unsupported cookie value falls through to `Accept-Language`."""
    req = _fake_request(accept_language="en", cookie="fr")
    assert get_language(req) == "en"


def test_cookie_invalid_no_header_falls_back_to_default():
    """An unsupported cookie and no header falls back to the default."""
    assert get_language(_fake_request(cookie="fr")) == "en"


def test_cookie_invalid_and_header_invalid():
    """Two unsupported sources still fall back to the default."""
    req = _fake_request(accept_language="de", cookie="fr")
    assert get_language(req) == "en"