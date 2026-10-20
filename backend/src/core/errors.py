from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match

from src.api.dependencies import get_language
from src.core.languages import TextArgs, get_error_detail
from src.shared.schemas import ErrorResponse

# Every error answers {"detail": "..."} translated to the user's language,
# the same shape FastAPI uses for its own errors

# Errors that Starlette raises by itself, with its default English text:
# 404 when the route doesn't exist, 405 when it exists but not with that method
ROUTING_ERRORS = {
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
}

# The methods a route can have, in the order they're listed in the "Allow" header of a 405
HTTP_METHODS = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")


# Translated {"detail": ...} error response
def error_response(
    request: Request,
    name: str,
    status_code: int,
    args: TextArgs | None = None,
) -> JSONResponse:
    language = get_language(request, request.query_params.get("lang"))
    return JSONResponse(
        {"detail": get_error_detail(name=name, language=language, args=args)},
        status_code=status_code,
    )


# Replaces slowapi's default handler, which answers {"error": ...} in English
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return error_response(request, "TOO_MANY_REQUESTS", 429)


# Replaces pydantic's English list of errors with one translated string
# loc is like ("body", "email") or ("query", "page"), the field is the last name in it
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields: list[str] = []
    for error in exc.errors():
        names = [part for part in error["loc"] if isinstance(part, str)]
        field = names[-1] if names else "body"
        if field not in fields:
            fields.append(field)
    return error_response(request, "VALIDATION_ERROR", 422, args={"detail": (", ".join(fields),)})


# Translates the routing errors above,
# any other HTTPException (like the ones raised by the services) keeps FastAPI's default handling
async def http_error_handler(request: Request, exc: StarletteHTTPException) -> Response:
    name = ROUTING_ERRORS.get(exc.status_code)
    # Only Starlette's own text ("Not Found"...), a custom 404 of ours keeps its message
    if name and exc.detail == HTTPStatus(exc.status_code).phrase:
        response = error_response(request, name, exc.status_code)
        response.headers.update(exc.headers or {})
        if exc.status_code == 405:
            response.headers["Allow"] = allowed_methods(request)
        return response
    return await http_exception_handler(request, exc)


# Every method of the path. Starlette's "Allow" only has the ones of the first route declared with it:
# a POST and a GET in two functions on the same path would answer "Allow: POST"
def allowed_methods(request: Request) -> str:
    return ", ".join(
        method for method in HTTP_METHODS
        if any(route.matches({**request.scope, "method": method})[0] == Match.FULL for route in request.app.routes)
    )


# Registers the error handlers in the app
# Unhandled errors (500) are handled in the log_requests middleware of main.py
def setup_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)  # pyright: ignore[reportArgumentType]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # pyright: ignore[reportArgumentType]
    app.add_exception_handler(StarletteHTTPException, http_error_handler)  # pyright: ignore[reportArgumentType]


# FastAPI documents its own 422 ({"detail": [...]}) on every route that receives data,
# but validation_error_handler answers {"detail": "..."}: the docs point those 422 to ErrorResponse
def setup_openapi(app: FastAPI) -> None:
    def openapi() -> dict[str, Any]:
        # Generated once, on the first visit to the docs
        if app.openapi_schema:
            return app.openapi_schema

        schema = FastAPI.openapi(app)
        schemas = schema.get("components", {}).get("schemas", {})

        if schemas.pop("HTTPValidationError", None):
            schemas.pop("ValidationError", None)
            schemas["ErrorResponse"] = ErrorResponse.model_json_schema()
            for operations in schema["paths"].values():
                for operation in operations.values():
                    response = operation.get("responses", {}).get("422")
                    if response:
                        response["content"]["application/json"]["schema"] = {
                            "$ref": "#/components/schemas/ErrorResponse",
                        }

        return schema

    app.openapi = openapi
