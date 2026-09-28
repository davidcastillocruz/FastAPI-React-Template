"""
Asynchronous SMTP email sender.

Provides a single entry point, `send_email`, that builds an HTML+plain
multipart email and delivers it via `aiosmtplib`. Transport-level
errors from the SMTP library are wrapped in `EmailSendError` so callers
have a single exception type to catch, regardless of whether the
failure was a connection issue, a TLS handshake failure, or an SMTP
rejection.

Credentials and connection settings come from `src.core.config`,
which reads them from environment variables at import time.
"""

from email.message import EmailMessage
from email.utils import formataddr, make_msgid

import aiosmtplib

from src.core import config


class EmailSendError(RuntimeError):
    """Raised when an email cannot be delivered.

    Wraps any error raised by `aiosmtplib` (SMTP-level or transport-level)
    so callers do not have to import and catch library-specific
    exceptions.
    """


async def send_email(
    *,
    to: str | list[str],
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> None:
    """Send an HTML email with a plain-text fallback.

    Builds a multipart message (`text/plain` + `text/html`) and delivers
    it over SMTP. All keyword-only arguments by design: the call sites
    are easier to read and less prone to positional mistakes.

    Args:
        to: Recipient address, or list of addresses.
        subject: Email subject line.
        html_body: HTML version of the body.
        text_body: Plain-text version. If omitted, the subject is used
            as a minimal fallback so the message still has a text part.

    Raises:
        ValueError: If no recipients are provided.
        EmailSendError: If the SMTP server rejects or fails to deliver
            the message, or if the connection cannot be established.
    """
    recipients = [to] if isinstance(to, str) else list(to)
    if not recipients:
        raise ValueError("At least one recipient is required.")

    message = EmailMessage()
    message["From"] = formataddr((config.SMTP_FROM_NAME, config.SMTP_FROM_EMAIL))
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message["Message-ID"] = make_msgid()

    message.set_content(text_body or subject)
    message.add_alternative(html_body, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            sender=config.SMTP_FROM_EMAIL,
            recipients=recipients,
            hostname=config.SMTP_HOST,
            port=config.SMTP_PORT,
            username=config.SMTP_USER or None,
            password=config.SMTP_PASSWORD or None,
            start_tls=config.SMTP_USE_TLS,
            timeout=config.SMTP_TIMEOUT,
        )
    except (aiosmtplib.SMTPException, OSError) as exc:
        raise EmailSendError(
            f"Failed to send email to {recipients}: {exc}"
        ) from exc