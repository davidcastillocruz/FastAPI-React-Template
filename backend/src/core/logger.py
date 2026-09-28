"""
Structured logging with colored console output.

Wraps the standard `logging` module to provide a small, ergonomic API
that fits the project's conventions:

- **Events are UPPERCASE** identifiers (e.g. `"USER_LOGGED_IN"`), so they
  are easy to grep and group in log aggregation tools.
- **Extras are passed as keyword arguments**, not as a dict. The wrapper
  collects them and forwards them to the underlying logger as a single
  `extras` attribute, which the formatter renders alongside the message.
- **Tracebacks** are attached automatically when calling `logger.exception(...)`
  inside an `except` block, or manually with `exc_info=True`.
- **DEBUG is suppressed outside development**, based on `PROJECT_MODE`.

The module configures the root logger on import: a single `StreamHandler`
writing to stdout with a custom formatter. Third-party loggers that are
noisy by default (uvicorn, sqlalchemy, aiosmtplib, httpx) are set to
`WARNING` to keep the console clean.

Usage:
    from src.core.logger import get_logger

    logger = get_logger(__name__)

    logger.debug("EMAIL_SEND_STARTED", to=to)
    logger.info("USER_LOGGED_IN", user_id=42, ip="1.2.3.4")
    logger.error("EMAIL_SEND_FAILED", to=to, error=str(exc))
    logger.exception("DB_QUERY_FAILED", query=sql)
"""

import logging
import sys

from src.core import config


# ---------------------------------------------------------------------------
# ANSI colors (cosmetic only)
# ---------------------------------------------------------------------------
_RESET = "\033[0m"
_DIM = "\033[2m"
_COLORS = {
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[1;31m",
}


class _Formatter(logging.Formatter):
    """Console formatter with color, timestamp, and structured extras.

    Renders each record as a single line:

        HH:MM:SS  LEVEL     logger.name  EVENT  {'key': 'value', ...}

    If the record carries exception or stack info, it is appended on
    subsequent lines, dimmed.
    """

    def format(self, record: logging.LogRecord) -> str:
        color = _COLORS.get(record.levelname, "")
        ts = self.formatTime(record, "%H:%M:%S")
        extras = getattr(record, "extras", None)
        extras_str = f"  {_DIM}{extras}{_RESET}" if extras else ""

        main = (
            f"{_DIM}{ts}{_RESET}  "
            f"{color}{record.levelname:<8}{_RESET}  "
            f"{record.name}  "
            f"{record.getMessage()}"
            f"{extras_str}"
        )

        if record.exc_info:
            main += f"\n{_DIM}{self.formatException(record.exc_info)}{_RESET}"
        if record.stack_info:
            main += f"\n{_DIM}{self.formatStack(record.stack_info)}{_RESET}"

        return main


# ---------------------------------------------------------------------------
# Root logger setup (runs on import)
# ---------------------------------------------------------------------------
# DEBUG is only enabled in development. In any other mode, INFO and above.
_IS_DEV = config.PROJECT_MODE == "development"
_LEVEL = logging.DEBUG if _IS_DEV else logging.INFO

_root = logging.getLogger()
_root.setLevel(_LEVEL)

# Guard against adding duplicate handlers if the module is imported twice.
if not _root.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setLevel(_LEVEL)
    _handler.setFormatter(_Formatter())
    _root.addHandler(_handler)

# Silence third-party loggers that are noisy at INFO/DEBUG.
for _name in ("uvicorn.access", "sqlalchemy.engine", "aiosmtplib", "httpx"):
    logging.getLogger(_name).setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
class Logger:
    """Wrapper around `logging.Logger` with a keyword-extras API.

    Instances are cheap: the wrapper only holds a reference to the
    underlying logger. Always create them via `get_logger`, never
    directly.
    """

    __slots__ = ("_logger",)

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def debug(self, event: str, **extras: object) -> None:
        """Log a DEBUG event. Suppressed outside development."""
        self._log(logging.DEBUG, event, extras)

    def info(self, event: str, **extras: object) -> None:
        """Log an INFO event."""
        self._log(logging.INFO, event, extras)

    def warning(self, event: str, **extras: object) -> None:
        """Log a WARNING event."""
        self._log(logging.WARNING, event, extras)

    def error(self, event: str, **extras: object) -> None:
        """Log an ERROR event without a traceback."""
        self._log(logging.ERROR, event, extras)

    def critical(self, event: str, **extras: object) -> None:
        """Log a CRITICAL event."""
        self._log(logging.CRITICAL, event, extras)

    def exception(self, event: str, **extras: object) -> None:
        """Log an ERROR event with the current traceback.

        Must be called from inside an `except` block. Outside of one,
        `exc_info=True` has no meaningful traceback to attach.
        """
        self._log(logging.ERROR, event, extras, exc_info=True)

    def _log(
        self,
        level: int,
        event: str,
        extras: dict[str, object],
        *,
        exc_info: bool = False,
    ) -> None:
        """Internal: short-circuit disabled levels and forward to logging."""
        # Avoid formatting the extras dict if the level is filtered out.
        if not self._logger.isEnabledFor(level):
            return
        self._logger.log(
            level,
            event,
            extra={"extras": extras or None},
            exc_info=exc_info,
        )


def get_logger(name: str) -> Logger:
    """Return a `Logger` bound to the given name.

    Convention: always pass `__name__` so the log line shows the module
    that emitted the event.

        logger = get_logger(__name__)
    """
    return Logger(name)