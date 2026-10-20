import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import ClassVar

from src.core import request_context
from src.core.settings import BASE_DIR, SRC_DIR, settings

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Every LogRecord has these; anything else came from `extra=`
# color_message: added by uvicorn on some of its own logs
# request_id, client_ip: added by RequestContextFilter, shown in their own column
_STANDARD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message", "asctime", "color_message", "request_id", "client_ip",
}


# Adds the id and the client IP of the current request to every log line ("-" outside a request)
class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_context.request_id.get()
        record.client_ip = request_context.client_ip.get()
        return True


# One line per log: time | level | request id and client IP | file:line or logger | message | extras as key=value
class AppFormatter(logging.Formatter):
    RESET = "\033[0m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    LEVEL_COLORS: ClassVar[dict[int, str]] = {
        logging.DEBUG: "\033[34m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[1;41m",
    }

    # Control characters written as text: a line break inside a message or an extra (e.g. a path with %0A)
    # would fake a new log line, an ANSI code (\x1b[...) would change the colors of the terminal,
    # and the Unicode line separators and direction marks would break or reorder the line in some viewers
    _CONTROL_CHARS: ClassVar[dict[int, str]] = {
        **{
            code: f"\\u{code:04x}" if code > 0xff else f"\\x{code:02x}"
            for code in [
                *range(0x20), *range(0x7f, 0xa0), 0x061c, 0x200e, 0x200f, 0x2028, 0x2029,
                *range(0x202a, 0x202f), *range(0x2066, 0x206a),
            ]
        },
        ord("\n"): "\\n",
        ord("\r"): "\\r",
        ord("\t"): "\\t",
    }

    def __init__(self, datefmt: str | None = None, use_colors: bool = False) -> None:
        super().__init__(datefmt=datefmt)
        self.use_colors = use_colors

    @classmethod
    def _escape(cls, value: object) -> str:
        return str(value).translate(cls._CONTROL_CHARS)

    def _paint(self, text: str, color: str) -> str:
        return f"{color}{text}{self.RESET}" if self.use_colors else text

    @staticmethod
    def _location(record: logging.LogRecord) -> str:
        path = Path(record.pathname).resolve()
        if path.is_relative_to(SRC_DIR):
            return f"{path.relative_to(BASE_DIR).as_posix()}:{record.lineno}"
        # uvicorn logs regular messages through "uvicorn.error", it's not an error
        return "uvicorn" if record.name == "uvicorn.error" else record.name

    @staticmethod
    def _extras(record: logging.LogRecord) -> dict[str, object]:
        return {
            k: v for k, v in record.__dict__.items()
            if k not in _STANDARD_ATTRS and not k.startswith("_")
        }

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno, "")

        line = " | ".join([
            self._paint(self.formatTime(record, self.datefmt), self.DIM),
            self._paint(f"{record.levelname:<8}", color),
            # Escaped too: uvicorn takes the client IP from X-Forwarded-For when the request comes from 127.0.0.1
            self._paint(
                self._escape(f"{getattr(record, 'request_id', '-')} {getattr(record, 'client_ip', '-')}"),
                self.DIM,
            ),
            self._paint(self._location(record), self.CYAN),
            self._escape(record.getMessage()),
        ])

        extras = self._extras(record)
        if extras:
            line += " | " + " ".join(
                f"{self._paint(k, self.MAGENTA)}={self._escape(v)}" for k, v in extras.items()
            )

        # The traceback keeps its lines, each one escaped and indented: an exception message can carry user input,
        # and a line break inside it can't fake a log line, every real log line starts at the first column
        if record.exc_info:
            traceback = "\n".join(
                f"    {self._escape(text)}" for text in self.formatException(record.exc_info).split("\n")
            )
            line += "\n" + self._paint(traceback, color)

        return line


# Every log of the process (the app's, uvicorn's, the libraries') goes through one handler with AppFormatter.
# uvicorn's access log is dropped: log_requests in main.py writes its own line with the request id
def setup_logging() -> None:
    use_colors = sys.stderr.isatty() and "NO_COLOR" not in os.environ

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "app": {
                "()": AppFormatter,
                "datefmt": DATE_FORMAT,
                "use_colors": use_colors,
            },
        },
        "filters": {
            "request_context": {"()": RequestContextFilter},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "app",
                "filters": ["request_context"],
            },
        },
        "root": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console"],
        },
        "loggers": {
            "uvicorn": {"handlers": [], "propagate": True},
            "uvicorn.error": {"handlers": [], "propagate": True},
            "uvicorn.access": {"handlers": [], "propagate": False},
            "sqlalchemy.engine": {"level": "WARNING"},
        },
    })
