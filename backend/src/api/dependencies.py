from typing import Annotated

from fastapi import Depends, Request

from src.core.settings import settings


# Client IP for logging and rate limiting
def get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# Language the API answers in, taken from the request
# Priority: ?lang= > "language" cookie > Accept-Language header > MAIN_LANGUAGE
def get_language(request: Request, lang: str | None = None) -> str:
    supported = settings.AVAILABLE_LANGUAGES
    tags: list[str] = []

    # 1. Query param: ?lang=es
    if lang:
        tags.append(lang.lower())

    # 2. Cookie saved when the user picked a language
    cookie_lang = request.cookies.get("language")
    if cookie_lang:
        tags.append(cookie_lang.lower())

    # 3. Accept-Language: "es-ES,es;q=0.9,en;q=0.8" -> ["es-es", "es", "en"]
    candidates: list[tuple[float, str]] = []
    # Spaces around ";" are valid ("es; q=0.9"). A quality of 0 means "not acceptable",
    # so q=0, a quality above 1 or one that isn't a number discards the tag
    for part in request.headers.get("accept-language", "").split(","):
        tag, *params = (piece.strip() for piece in part.split(";"))
        quality = 1.0
        for param in params:
            if param.lower().startswith("q="):
                try:
                    quality = float(param[2:])
                except ValueError:
                    quality = -1.0
        tag = tag.lower()
        if tag and tag != "*" and 0 < quality <= 1:
            candidates.append((quality, tag))

    # Highest quality first, ties keep the browser's order (sorted is stable)
    tags.extend(tag for _, tag in sorted(candidates, key=lambda c: -c[0]))

    # First supported tag wins, trying the base language too ("es-es" -> "es")
    for tag in tags:
        for option in (tag, tag.split("-")[0]):
            if option in supported:
                return option

    # 4. Fallback
    return settings.MAIN_LANGUAGE


# Language of the request, in an endpoint: language: Language
Language = Annotated[str, Depends(get_language)]
