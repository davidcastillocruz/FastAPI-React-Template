import logging
import re

from aiosmtplib import SMTPRecipientRefused, SMTPRecipientsRefused
from fastapi_mail import FastMail, MessageType
from fastapi_mail.errors import ConnectionErrors

from src.core.logger import AppFormatter
from src.mail.sender import _mask_email, send_email
from src.mail.templates.demo_email import demo_email
from src.mail.templates.demo_email.demo_email import build_demo_email


def flaps(body: str) -> list[str]:
    # Content of every flap of the board, in order
    return re.findall(r'text-align:center;">(.*?)</td>', body)


def test_mask_email():
    assert _mask_email("ana@test.dev") == "a***@test.dev"
    assert _mask_email("@test.dev") == "***@test.dev"
    assert _mask_email("not-an-email") == "***"


def test_demo_email_in_each_language():
    subject, body = build_demo_email("es")

    assert subject == "Tu email de prueba"
    assert '<html lang="es">' in body and "¡Funciona!" in body
    assert flaps(body) == list("ENTREGADO")
    assert build_demo_email("en")[0] == "Your test email"


def test_demo_email_escapes_the_texts_once(monkeypatch):
    texts = {"subject": "A & B", "title": "<b>", "text": "x", "board": "y", "status": "a&'", "footer": "z"}
    monkeypatch.setattr(demo_email, "get_response", lambda name, language: texts)

    subject, body = build_demo_email("en")

    assert subject == "A & B"
    assert "<b>" not in body and "&lt;b&gt;" in body
    assert flaps(body) == ["A", "&amp;", "&#x27;"]


async def test_send_email_sends_the_html_and_logs_masked_recipients(monkeypatch, caplog):
    sent = []

    async def accepted(self, message):
        sent.append(message)

    monkeypatch.setattr(FastMail, "send_message", accepted)
    with caplog.at_level(logging.INFO, logger="src.mail.sender"):
        await send_email("Subject", ["ana@test.dev"], "<p>body</p>")

    message = sent[0]
    assert [recipient.email for recipient in message.recipients] == ["ana@test.dev"]
    assert message.subject == "Subject" and message.body == "<p>body</p>" and message.subtype == MessageType.html
    assert caplog.records[-1].getMessage() == "Email sent"
    assert caplog.records[-1].recipients == ["a***@test.dev"]


async def test_send_email_failures_never_log_the_plain_address(monkeypatch, caplog):
    errors = [
        ConnectionErrors("Connection refused"),
        SMTPRecipientsRefused([SMTPRecipientRefused(550, "5.1.1 <ana@test.dev>: unknown", "ana@test.dev")]),
        RuntimeError("could not deliver to ana@test.dev"),
    ]

    for error in errors:
        async def failing(self, message, error=error):
            raise error

        monkeypatch.setattr(FastMail, "send_message", failing)
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.mail.sender"):
            # Errors are logged, not raised: it runs as a background task
            await send_email("Subject", ["ana@test.dev"], "<p>body</p>")

        record = caplog.records[-1]
        assert record.levelno == logging.ERROR and record.exc_info is None
        # Formatted like the app does: the message, the args and every extra
        assert "ana@test.dev" not in AppFormatter().format(record)
        if not isinstance(error, ConnectionErrors):
            assert record.recipients == ["a***@test.dev"]
        # Its own branch, not the generic one: aiosmtplib gives a list of SMTPRecipientRefused, one code each
        if isinstance(error, SMTPRecipientsRefused):
            assert record.getMessage() == "Mail server refused the recipients" and record.codes == [550]
