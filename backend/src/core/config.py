"""
Application configuration, loaded from environment variables.

Values are read once at import time. If a required variable is missing
or misconfigured, the module raises at import time so the process
fails before serving any traffic, rather than at the first request.
"""

import os

from dotenv import load_dotenv

# Load `.env` from the current working directory. In tests, `.env.test`
# is loaded by `conftest.py` before this module is imported.
load_dotenv()


# ---------------------------------------------------------------------------
# Project info
# ---------------------------------------------------------------------------
PROJECT_NAME: str = os.getenv("PROJECT_NAME", "FastAPI-React-Template")
PROJECT_DESCRIPTION: str = os.getenv("PROJECT_DESCRIPTION", "A Development Template")
PROJECT_VERSION: str = os.getenv("PROJECT_VERSION", "1.0.0")


# ---------------------------------------------------------------------------
# Project config
# ---------------------------------------------------------------------------
PROJECT_MODE: str = os.getenv("PROJECT_MODE", "development")

PROJECT_MAIN_LANGUAGE: str = os.getenv("PROJECT_MAIN_LANGUAGE", "en")
PROJECT_SUPPORTED_LANGUAGES: list[str] = [
    x.strip()
    for x in os.getenv("PROJECT_SUPPORTED_LANGUAGES", "en,es").split(",")
    if x.strip()
]


if PROJECT_MAIN_LANGUAGE not in PROJECT_SUPPORTED_LANGUAGES:
    raise RuntimeError(
        f"PROJECT_MAIN_LANGUAGE='{PROJECT_MAIN_LANGUAGE}' must be one of "
        f"PROJECT_SUPPORTED_LANGUAGES={PROJECT_SUPPORTED_LANGUAGES}"
    )


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_URL_ASYNC: str = os.getenv("DATABASE_URL_ASYNC", "")

if not DATABASE_URL_ASYNC:
    raise RuntimeError(
        "DATABASE_URL_ASYNC is not set. Add it to your .env file. "
        "Example: postgresql+asyncpg://user:pass@localhost:5432/mydb"
    )


# ---------------------------------------------------------------------------
# Email / SMTP
# ---------------------------------------------------------------------------
SMTP_HOST: str = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
SMTP_TIMEOUT: int = int(os.getenv("SMTP_TIMEOUT", "10"))

SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "no-reply@example.com")
SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", PROJECT_NAME)