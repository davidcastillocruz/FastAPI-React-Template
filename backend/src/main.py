"""
FastAPI application entrypoint.

Wires together:

- **Startup**: prints a banner, loads translations into memory, and
  yields control to the server. Shutdown prints a farewell message.
- **Middlewares**: CORS (frontend origins), trusted hosts (disabled in
  test mode), and gzip compression for large payloads.
- **Routers**: the API is mounted under `src.api.routers`. New routers
  should be added next to `test.router`.
- **Validation handler**: converts Pydantic `RequestValidationError`s
  into translated JSON responses when a matching entry exists. Errors
  without a translation fall back to Pydantic's default payload.
- **Health check**: a lightweight `/health` endpoint for probes and
  load balancers.

Interactive docs (`/docs`, `/redoc`, `/openapi.json`) are disabled
unless `PROJECT_MODE == "development"`.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.api.routers import test
from src.core import config, language_data
from src.core.language_manager import get_exception

# ---------------------------------------------------------------------------
# Console
# ---------------------------------------------------------------------------
console = Console()


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
def _build_banner() -> None:
    """Print the startup banner with project metadata.

    Purely cosmetic. Uses `rich` to render a small table with the
    project name, version, mode, and docs URL.
    """
    table = Table(show_header=False, show_edge=False, box=None, padding=(0, 1))
    table.add_column(justify="left", no_wrap=True)
    table.add_column(justify="left", no_wrap=True)

    table.add_row("🚀", f"[bold cyan]Project:[/] {config.PROJECT_NAME}")
    table.add_row("📦", f"[bold cyan]Version:[/] {config.PROJECT_VERSION}")
    table.add_row("🌐", f"[bold cyan]Mode:   [/] {config.PROJECT_MODE}")
    table.add_row("✅", f"[bold green]Status: [/] API ready for takeoff")
    table.add_row(
        "📚",
        f"[bold cyan]Docs:   [/] [link=http://localhost:8000/docs]"
        f"http://localhost:8000/docs[/link]",
    )

    panel = Panel(
        table,
        title="[bold white]Startup[/]",
        subtitle=f"[dim]{config.PROJECT_NAME} v{config.PROJECT_VERSION}[/dim]",
        border_style="cyan",
        expand=False,
        padding=(1, 2),
    )

    console.print()
    console.print(panel)
    console.print()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup and shutdown logic.

    Startup:

    - Print the banner.
    - Load translations into memory via `language_data.load()`. This
      happens once per process; any change to the JSON requires a
      restart (or a manual call to `load()` again).

    Shutdown:

    - Print a farewell message.
    """
    # --- Startup ---
    _build_banner()
    language_data.load()

    yield

    # --- Shutdown ---
    console.print(
        f"\n👋  [bold yellow]{config.PROJECT_NAME}[/] is shutting down... "
        f"[dim]see you soon![/dim]\n"
    )


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title=config.PROJECT_NAME,
    description=config.PROJECT_DESCRIPTION,
    version=config.PROJECT_VERSION,
    lifespan=lifespan,
    # Hide interactive docs in production for security.
    docs_url="/docs" if config.PROJECT_MODE == "development" else None,
    redoc_url="/redoc" if config.PROJECT_MODE == "development" else None,
    openapi_url="/openapi.json" if config.PROJECT_MODE == "development" else None,
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# In production, list real domains only. Never combine "*" with
# `allow_credentials=True`; browsers reject that combination.
origins = [
    "http://localhost:5173",   # Vite dev server
    "http://127.0.0.1:5173",
    "null",                    # Allows `file://`-served HTML during local testing
    # "https://your-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,   # Allow cookies and the Authorization header
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Trusted hosts
# ---------------------------------------------------------------------------
# Protects against Host header injection. Skipped in test mode so the
# in-process test client can use an arbitrary host without extra config.
if config.PROJECT_MODE != "test":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.your-domain.com"],
    )


# ---------------------------------------------------------------------------
# GZip
# ---------------------------------------------------------------------------
# Compress responses larger than 1 KB. Mostly benefits JSON payloads.
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
# from src.api.v1.router import api_router
app.include_router(test.router)


# ---------------------------------------------------------------------------
# Validation handler
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    """Translate Pydantic validation errors when a matching entry exists.

    Iterates over `exc.errors()`. For each error, tries to resolve its
    `type` as a `name` in the `"exceptions"` section of the translations
    store. The first one that produces a payload is returned as the
    response body.

    Validation errors whose `type` is not a translation name — which
    includes every standard Pydantic error such as `"missing"` or
    `"string_type"` — are skipped. If none of the errors match, the
    handler falls back to Pydantic's default payload
    (`{"detail": [...]}`), which is still useful to the client.

    Translation names are not whitelisted here. When a custom
    `PydanticCustomError` is introduced in a schema and its code matches
    an entry in `language_responses.json`, it is translated
    automatically. If the code has no entry, it falls through to the
    fallback like any other untranslated error.

    Errors raised by `get_exception` other than `KeyError` (which
    indicates a missing name) are not caught here: they represent real
    failures in the translation system and should surface as 500s.
    """
    for err in exc.errors():
        error_type = err.get("type")
        if not error_type:
            continue
        try:
            content = get_exception(name=error_type, request=request)
        except KeyError:
            # This validation error has no translation entry. Skip it
            # and try the next one.
            continue
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=content,
        )

    # Fallback: none of the errors matched a translation entry.
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": exc.errors()},
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Liveness probe endpoint.

    Returns a small JSON payload with the service name and version.
    Intended for Docker healthchecks, Kubernetes probes, and uptime
    monitors. Does not touch the database or any external dependency.
    """
    return {
        "status": "ok",
        "service": config.PROJECT_NAME,
        "version": config.PROJECT_VERSION,
    }