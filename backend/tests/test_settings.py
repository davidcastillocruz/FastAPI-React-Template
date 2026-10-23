import pytest
from pydantic import ValidationError

from src.core.settings import Settings

VALID = {
    "APP_TITLE": "App", "APP_DESCRIPTION": "Description", "APP_MODE": "development",
    "POSTGRES_USER": "user", "POSTGRES_PASSWORD": "secret", "POSTGRES_DB": "app",
    "DATABASE_HOST": "db", "DATABASE_PORT": "5432", "DATABASE_POOL_SIZE": "5", "DATABASE_MAX_OVERFLOW": "10",
    "MAIN_LANGUAGE": "en", "AVAILABLE_LANGUAGES": "en,es", "RATE_LIMIT_STORAGE_URI": "memory://",
    "CORS_ORIGINS": "http://localhost:5173",
    "MAIL_USERNAME": "user", "MAIL_PASSWORD": "secret", "MAIL_FROM": "app@test.dev", "MAIL_SERVER": "mailpit",
    "MAIL_PORT": "1025", "MAIL_START_TLS": "false", "MAIL_SSL_TLS": "false",
}


# Only these values: no .env files and no variables of the environment
@pytest.fixture
def make(monkeypatch):
    for name in VALID:
        monkeypatch.delenv(name, raising=False)

    def make(**changes) -> Settings:
        values = {k: v for k, v in {**VALID, **changes}.items() if v is not None}
        for name, value in values.items():
            monkeypatch.setenv(name, value)
        return Settings(_env_file=None)  # pyright: ignore[reportCallIssue]

    return make


def test_valid_settings(make):
    settings = make()

    assert settings.DATABASE_PORT == 5432 and settings.MAIL_SSL_TLS is False
    assert settings.LOG_LEVEL == "DEBUG"


def test_lists_and_text_are_normalized(make):
    settings = make(APP_MODE=" Production ", MAIN_LANGUAGE="ES", AVAILABLE_LANGUAGES="en, ES,",
                    CORS_ORIGINS="http://Localhost:5173/, https://app.com ,", MAIL_SSL_TLS="true")

    assert settings.APP_MODE == "production" and settings.LOG_LEVEL == "INFO"
    assert settings.MAIN_LANGUAGE == "es" and settings.AVAILABLE_LANGUAGES == ["en", "es"]
    assert settings.CORS_ORIGINS == ["http://localhost:5173", "https://app.com"]


def test_database_url_escapes_the_password(make):
    settings = make(POSTGRES_PASSWORD="p@ss/word:1")

    url = settings.DATABASE_URL.render_as_string(hide_password=False)

    assert url == "postgresql+asyncpg://user:p%40ss%2Fword%3A1@db:5432/app"
    assert settings.DATABASE_URL.password == "p@ss/word:1"


@pytest.mark.parametrize("changes", [
    {"MAIL_PASSWORD": None},
    {"APP_MODE": "staging"},
    {"DATABASE_PORT": "abc"},
    {"DATABASE_POOL_SIZE": "0"},
    {"DATABASE_MAX_OVERFLOW": "-1"},
    {"MAIN_LANGUAGE": "fr"},
    {"MAIL_START_TLS": "true", "MAIL_SSL_TLS": "true"},
    {"APP_MODE": "production"},
    {"CORS_ORIGINS": " , "},
    {"CORS_ORIGINS": "localhost:5173"},
    {"CORS_ORIGINS": "http://localhost:5173/app"},
], ids=[
    "missing variable", "unknown mode", "port not a number", "pool too small", "negative overflow",
    "main language not available", "both tls", "production without tls",
    "no origin", "origin without scheme", "origin with a path",
])
def test_invalid_settings_stop_startup(make, changes):
    with pytest.raises(ValidationError):
        make(**changes)


# With credentials allowed, "*" would let any site call the API with the user's cookies
@pytest.mark.parametrize("origins", ["*", "http://localhost:5173,null"])
def test_any_origin_is_rejected(make, origins):
    with pytest.raises(ValidationError, match='"\\*" and "null" are not allowed'):
        make(CORS_ORIGINS=origins)


def test_errors_hide_the_values(make):
    with pytest.raises(ValidationError) as error:
        make(DATABASE_PORT="secret-value")

    assert "DATABASE_PORT" in str(error.value) and "secret-value" not in str(error.value)
