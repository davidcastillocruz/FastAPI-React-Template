import asyncio
import logging
import re
import sys

import pytest

from src.core import request_context
from src.core.logger import AppFormatter, RequestContextFilter, setup_logging
from src.core.settings import SRC_DIR

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def record(msg="hello", args=(), level=logging.INFO, pathname=None, name="app", exc_info=None, **extra):
    log = logging.LogRecord(name, level, pathname or str(SRC_DIR / "core" / "x.py"), 42, msg, args, exc_info)
    for key, value in extra.items():
        setattr(log, key, value)
    return log


def line(log: logging.LogRecord, colors: bool = False) -> str:
    RequestContextFilter().filter(log)
    return AppFormatter(datefmt="%Y", use_colors=colors).format(log)


def test_line_shape():
    parts = line(record()).split(" | ")

    assert parts[1].strip() == "INFO" and parts[2] == "- -"
    assert parts[3] == "src/core/x.py:42" and parts[4] == "hello"


def test_args_and_extras():
    assert line(record("%s %d", ("GET", 200), duration_ms=1.5)).endswith("| GET 200 | duration_ms=1.5")
    assert line(record()).endswith("| hello")


def test_internal_attributes_are_not_extras():
    text = line(record(color_message="x", _private=1))

    assert "color_message" not in text and "_private" not in text and "taskName" not in text


def test_control_characters_are_escaped():
    token = request_context.client_ip.set("1.2.3.4\nFAKE")
    try:
        text = line(record("%s", ("/a\nFAKE\r\x1b[2J\t\x9b",), path="x\ny"))
    finally:
        request_context.client_ip.reset(token)

    assert not any(char in text for char in "\n\r\x1b\x9b")
    assert "/a\\nFAKE\\r\\x1b[2J\\t\\x9b" in text and "path=x\\ny" in text and "1.2.3.4\\nFAKE" in text


def test_non_ascii_is_kept():
    assert "cañón ü 日本" in line(record("cañón ü 日本"))


def test_each_task_sees_its_own_request_id():
    async def handle(i: int) -> str:
        request_context.request_id.set(f"id{i}")
        await asyncio.sleep(0.01)
        return line(record())

    async def main():
        return await asyncio.gather(*(handle(i) for i in range(20)))

    lines = asyncio.run(main())

    assert all(f" | id{i} - | " in text for i, text in enumerate(lines))
    assert request_context.request_id.get() == "-"


def test_location_outside_src():
    assert line(record(pathname="/site-packages/lib.py", name="sqlalchemy.pool")).split(" | ")[3] == "sqlalchemy.pool"
    assert line(record(pathname="/site-packages/uvicorn/server.py", name="uvicorn.error")).split(" | ")[3] == "uvicorn"


def test_traceback_goes_below_the_line():
    try:
        raise ValueError("bad")
    except ValueError:
        log = record("boom", level=logging.ERROR, exc_info=sys.exc_info())

    first, rest = line(log).split("\n", 1)

    assert first.endswith("| boom") and "Traceback" in rest and "ValueError: bad" in rest


def test_traceback_lines_are_escaped():
    try:
        raise ValueError("bad\r\nFAKE \x1b[2J \u2028 \u202e \u200f")
    except ValueError:
        log = record("boom", level=logging.ERROR, exc_info=sys.exc_info())

    text = line(log)

    assert not any(char in text for char in "\r\x1b\u2028\u202e\u200f")
    assert "ValueError: bad\\r" in text and "FAKE \\x1b[2J \\u2028 \\u202e \\u200f" in text
    # The traceback keeps its lines, all indented: only the log line starts at the first column
    lines = text.split("\n")
    assert len(lines) > 3 and all(text.startswith("    ") for text in lines[1:])


def test_colors():
    plain = line(record())
    colored = line(record(), colors=True)

    assert "\x1b" not in plain and "\x1b[32m" in colored and ANSI.sub("", colored) == plain


# setup_logging replaces the handlers of the whole process: the ones of the app are restored afterwards,
# or the next logs would go to the closed capture of this test
@pytest.fixture
def restore_logging():
    handlers = logging.root.handlers[:]
    yield
    logging.root.handlers = handlers


def test_setup_logging(capsys, monkeypatch, restore_logging):
    monkeypatch.setenv("NO_COLOR", "1")
    early = logging.getLogger("created.before.setup")
    setup_logging()

    logging.getLogger("src.test").debug("debug line", extra={"user_id": 7})
    logging.getLogger("uvicorn.error").info("Started server process")
    logging.getLogger("uvicorn.access").info("GET / 200")
    logging.getLogger("sqlalchemy.engine").info("SELECT 1")
    early.warning("still here")
    token = request_context.request_id.set("abc123")
    logging.getLogger("src.test").info("inside a request")
    request_context.request_id.reset(token)
    err = capsys.readouterr().err

    assert "debug line | user_id=7" in err
    assert "uvicorn | Started server process" in err
    assert "still here" in err
    # The handler adds the request context to every line
    assert "| abc123 - | src.test | inside a request" in err
    assert "GET / 200" not in err and "SELECT 1" not in err


# Docker's tty: true gives the backend a terminal, a file or a pipe (CI) gets plain lines
@pytest.mark.parametrize(
    "terminal, no_color, colored", [(True, False, True), (True, True, False), (False, False, False)],
)
def test_colors_only_in_a_terminal_without_no_color(capsys, monkeypatch, restore_logging, terminal, no_color, colored):
    monkeypatch.setattr(sys.stderr, "isatty", lambda: terminal)
    if no_color:
        monkeypatch.setenv("NO_COLOR", "1")
    else:
        monkeypatch.delenv("NO_COLOR", raising=False)
    setup_logging()

    logging.getLogger("src.test").warning("hello")

    assert ("\x1b[" in capsys.readouterr().err) is colored
