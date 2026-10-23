import json

import pytest
from starlette.requests import Request

from src.api.dependencies import get_language
from src.core import languages
from src.core.languages import get_error_detail, get_response, setup_language_system


def request_with(headers: dict[str, str] | None = None, cookies: str | None = None) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    if cookies:
        raw.append((b"cookie", cookies.encode()))
    return Request({"type": "http", "headers": raw, "query_string": b""})


# --- get_language: ?lang= > cookie > Accept-Language > MAIN_LANGUAGE ---

def test_language_priority():
    request = request_with({"Accept-Language": "en"}, cookies="language=en")
    assert get_language(request, "ES") == "es"
    assert get_language(request_with({"Accept-Language": "en"}, cookies="language=es")) == "es"
    assert get_language(request_with({"Accept-Language": "es-ES,es;q=0.9,en;q=0.8"})) == "es"


def test_language_quality_and_fallbacks():
    assert get_language(request_with({"Accept-Language": "fr;q=1, en;q=0.5, es;q=0.9"})) == "es"
    # q=0 means "not acceptable": es is skipped although fr comes first and isn't available
    assert get_language(request_with({"Accept-Language": "fr, es;q=0"})) == "en"
    # A regional tag falls back to its base language
    assert get_language(request_with({"Accept-Language": "es-MX"})) == "es"
    assert get_language(request_with({"Accept-Language": "*, fr, es;q=bad"})) == "en"


def test_unsupported_query_and_cookie_fall_through_to_the_header():
    # An old cookie or a hand-written ?lang= with a language the app doesn't have
    request = request_with({"Accept-Language": "es"}, cookies="language=fr")
    assert get_language(request, "pt") == "es"


def test_language_header_with_spaces_and_wrong_qualities():
    assert get_language(request_with({"Accept-Language": "en; q=0.5, es ; q=0.9"})) == "es"
    assert get_language(request_with({"Accept-Language": "es;q=inf, en"})) == "en"
    assert get_language(request_with({"Accept-Language": "es;q=nan, es;q=2"})) == "en"
    assert get_language(request_with(), "fr") == "en"
    assert get_language(request_with()) == "en"


# --- setup_language_system: every broken file stops the startup ---

@pytest.fixture
def translations(tmp_path, monkeypatch):
    # Points the system to a temporary src/ and restores the real translations afterwards
    real = languages.LANGUAGE_DATA
    monkeypatch.setattr(languages, "SRC_DIR", tmp_path / "src")
    monkeypatch.setattr(languages, "BASE_DIR", tmp_path)
    folder = tmp_path / "src" / "translations"
    folder.mkdir(parents=True)

    def write(data, name="test_translations.json", raw: str | None = None):
        (folder / name).write_text(raw if raw is not None else json.dumps(data), encoding="utf-8")

    yield write
    languages.LANGUAGE_DATA = real


def entry(en: object, es: object) -> dict[str, object]:
    return {"en": en, "es": es}


def test_valid_file_loads(translations):
    translations({"HELLO": entry({"detail": "Hi %s"}, {"detail": "Hola %s"})})
    setup_language_system()

    assert get_response("HELLO", "es", {"detail": ("Ana",)}) == {"detail": "Hola Ana"}
    assert get_error_detail("HELLO", "en") == "Hi %s"


def test_extra_language_is_ignored(translations):
    # fr isn't in AVAILABLE_LANGUAGES: it isn't checked (a number would stop the startup) and isn't loaded
    translations({"HELLO": {"en": {"detail": "Hi"}, "es": {"detail": "Hola"}, "fr": {"detail": 1}}})
    setup_language_system()

    assert set(languages.LANGUAGE_DATA["HELLO"]) == {"en", "es"}


VALID_ENTRY = json.dumps(entry({"detail": "x"}, {"detail": "x"}))


# Each file is broken in only one way, and match= checks that it's that check the one that stops it
@pytest.mark.parametrize("data, raw, error, match", [
    (None, "{bad json", json.JSONDecodeError, "Expecting"),
    (None, f'{{"A": {VALID_ENTRY}, "A": {VALID_ENTRY}}}', ValueError, r"Repeated keys: \['A'\]"),
    ([], None, TypeError, r"Expected a dict in .+, got list"),
    ({"A": "text"}, None, TypeError, r"\[A\], got str"),
    ({"A": {"en": {"detail": "x"}}}, None, ValueError, "missing languages"),
    ({"A": entry({"detail": "x"}, "text")}, None, TypeError, r"\[A\]\[es\], got str"),
    ({"A": entry({"detail": 1}, {"detail": "x"})}, None, TypeError, "Expected a string"),
    ({"A": entry({"detail": "x"}, {"other": "x"})}, None, ValueError, "different texts"),
    ({"A": {"EN": {"detail": "x"}, **entry({"detail": "x"}, {"detail": "x"})}}, None, ValueError, "not in lowercase"),
    ({"A": entry({"detail": "%s"}, {"detail": "x"})}, None, ValueError, "different number of %s"),
    ({"A": entry({"detail": "50% %s"}, {"detail": "50% %s"})}, None, ValueError, "can't be filled"),
], ids=[
    "invalid json", "repeated key", "not an object", "entry not an object", "missing language",
    "texts not an object", "text not a string", "different texts", "uppercase language code",
    "different placeholders", "unfillable",
])
def test_broken_file_stops_startup(translations, data, raw, error, match):
    translations(data, raw=raw)

    with pytest.raises(error, match=match):
        setup_language_system()


def test_file_with_a_bom_loads(translations):
    # Some editors save the files with a BOM at the start
    translations(None, raw="\ufeff" + json.dumps({"HELLO": entry({"detail": "Hi"}, {"detail": "Hola"})}))
    setup_language_system()

    assert get_error_detail("HELLO", "es") == "Hola"


def test_same_name_in_two_files_stops_startup(translations):
    translations({"A": entry({"detail": "x"}, {"detail": "x"})}, name="one_translations.json")
    translations({"A": entry({"detail": "y"}, {"detail": "y"})}, name="two_translations.json")

    with pytest.raises(ValueError, match=r"is in src/translations/one_translations\.json and"):
        setup_language_system()


def test_no_files_stops_startup(translations, tmp_path):
    (tmp_path / "src" / "translations").rmdir()

    with pytest.raises(FileNotFoundError):
        setup_language_system()


def test_literal_percent_works_when_escaped(translations):
    translations({"A": entry({"detail": "50%% off for %s"}, {"detail": "50%% para %s"})})
    setup_language_system()

    assert get_error_detail("A", "en", {"detail": ("Ana",)}) == "50% off for Ana"


def test_unknown_response_and_wrong_args_fail(translations):
    translations({"A": entry({"detail": "x"}, {"detail": "x"})})
    setup_language_system()

    with pytest.raises(KeyError):
        get_response("NOPE", "en")
    with pytest.raises(TypeError):
        get_response("A", "en", {"detail": ("extra",)})


# The test client doesn't run the lifespan (conftest loads the languages itself): this checks the app's own startup
async def test_startup_loads_the_languages(monkeypatch):
    from src.main import app

    monkeypatch.setattr(languages, "LANGUAGE_DATA", {})
    async with app.router.lifespan_context(app):
        assert "NOT_FOUND" in languages.LANGUAGE_DATA
