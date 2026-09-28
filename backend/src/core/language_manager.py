"""
Language resolution and translation lookups.

This module exposes the public API used by route handlers and services
to fetch translated payloads. It combines two responsibilities:

- **Language resolution** (`get_language`): pick the language for the
  current request based on a cookie, the `Accept-Language` header, or a
  fallback, in that order of priority.
- **Translation lookup** (`get_response`, `get_exception`): fetch a
  payload from the in-memory store, fall back to the default language
  if the requested one is missing, and substitute `%s` placeholders.

The module never touches the disk. All data is read from
`language_data`, which is loaded once at app startup.
"""

from fastapi import Request

from src.core import config, language_data
from src.core.logger import get_logger
from src.core.request_utils import get_client_ip

logger = get_logger(__name__)

DEFAULT_LANG = config.PROJECT_MAIN_LANGUAGE
SUPPORTED_LANGUAGES = set(config.PROJECT_SUPPORTED_LANGUAGES)

# Name of the cookie used to override the browser's preferred language.
LANGUAGE_COOKIE = "language"


def _normalize_lang(value: str) -> str:
    """Reduce a raw language string to its base form.

    Strips quality parameters, whitespace, case, and region subtags so
    that any of `"es-MX"`, `"es-MX;q=0.9"`, `" ES "`, or `"en"` end up as
    a comparable base code (`"es"`, `"es"`, `"es"`, `"en"`).

    Args:
        value: Raw language string from a cookie or an `Accept-Language`
            header item.

    Returns:
        Base language code in lowercase, without region or quality.
    """
    return value.split(";")[0].strip().lower().split("-")[0]


def get_language(request: Request, default: str = DEFAULT_LANG) -> str:
    """Resolve the language for the current request.

    Priority order:

    1. The `language` cookie, if present and supported.
    2. The `Accept-Language` header, first supported entry wins.
    3. The `default` argument.

    Args:
        request: Incoming FastAPI request.
        default: Fallback language if the cookie and header do not yield
            a supported code.

    Returns:
        A supported base language code, or `default` if none matched.
    """
    cookie = request.cookies.get(LANGUAGE_COOKIE)
    if cookie:
        lang = _normalize_lang(cookie)
        if lang in SUPPORTED_LANGUAGES:
            return lang

    header = request.headers.get("accept-language", "")
    if not header:
        return default

    for part in header.split(","):
        lang = _normalize_lang(part)
        if lang and lang in SUPPORTED_LANGUAGES:
            return lang

    return default


def _resolve_entry_id(
    section: str,
    entry_id: int | None,
    name: str | None,
) -> int:
    """Resolve the numeric entry id from either `entry_id` or `name`.

    Callers must provide exactly one of the two. Providing both or
    neither is a programming error and raises `ValueError`.

    Args:
        section: Translation section, used when resolving a `name`.
        entry_id: Numeric id, if provided directly.
        name: Symbolic name to resolve, if provided.

    Returns:
        The numeric entry id.

    Raises:
        ValueError: If both or neither of `entry_id` and `name` are given.
        KeyError: If `name` does not exist in the given section.
    """
    if entry_id is not None and name is not None:
        raise ValueError("Provide either 'entry_id' or 'name', not both")

    if name is not None:
        resolved = language_data.get_entry_id_by_name(section, name)
        if resolved is None:
            raise KeyError(f"Unknown name '{name}' in section '{section}'")
        return resolved

    if entry_id is None:
        raise ValueError("Either 'entry_id' or 'name' must be provided")

    return entry_id


def get_data(
    section: str,
    request: Request,
    entry_id: int | None = None,
    name: str | None = None,
    placeholders: list[dict] | None = None,
    default: str = DEFAULT_LANG,
) -> dict:
    """Fetch a translated payload and substitute its placeholders.

    Resolves the request language, looks up the entry (either by id or
    by name), falls back to `default` if the requested language is
    missing, and replaces `%s` markers with the provided values.

    The payload is copied before substitution so the cached entry is
    never mutated. Callers receive a fresh dict every time.

    Args:
        section: Translation section (e.g. `"responses"`, `"exceptions"`).
        request: Incoming FastAPI request, used for language resolution
            and logging context.
        entry_id: Numeric id of the entry. Mutually exclusive with `name`.
        name: Symbolic name of the entry. Mutually exclusive with `entry_id`.
        placeholders: List of dicts mapping payload keys to the values
            that replace their `%s` markers. Each dict handles one or
            more keys. Missing keys are left untouched.
        default: Fallback language if the request language is not
            available for this entry.

    Returns:
        A copy of the payload with placeholders substituted.

    Raises:
        ValueError: If both or neither of `entry_id` and `name` are given.
        KeyError: If the entry or its translations do not exist.
    """
    try:
        resolved_id = _resolve_entry_id(section, entry_id, name)
        lang = get_language(request=request, default=default)

        raw = (
            language_data.get_data_raw(section, resolved_id, lang)
            or language_data.get_data_raw(section, resolved_id, default)
        )

        if raw is None:
            raise KeyError(
                f"No translation for '{lang}' nor default '{default}' "
                f"at {section}[{resolved_id}]"
            )

        # Copy: the cached payload must never be mutated.
        response = dict(raw)

        for placeholder in (placeholders or []):
            for key, values in placeholder.items():
                response[key] = response[key] % values

        return response
    except Exception:
        client_ip = get_client_ip(request)
        logger.exception(
            "ERROR_GETTING_LANGUAGE_DATA",
            ip=client_ip,
            section=section,
            entry_id=entry_id,
            name=name,
            placeholders=placeholders,
        )
        raise


def get_response(
    request: Request,
    entry_id: int | None = None,
    name: str | None = None,
    placeholders: list[dict] | None = None,
) -> dict:
    """Fetch a translated response from the `"responses"` section.

    Thin wrapper around `get_data`. See it for details on arguments,
    return value, and exceptions.
    """
    return get_data(
        section="responses",
        request=request,
        entry_id=entry_id,
        name=name,
        placeholders=placeholders,
    )


def get_exception(
    request: Request,
    entry_id: int | None = None,
    name: str | None = None,
    placeholders: list[dict] | None = None,
) -> dict:
    """Fetch a translated exception from the `"exceptions"` section.

    Thin wrapper around `get_data`. See it for details on arguments,
    return value, and exceptions.
    """
    return get_data(
        section="exceptions",
        request=request,
        entry_id=entry_id,
        name=name,
        placeholders=placeholders,
    )