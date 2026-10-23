import logging

from aiosmtplib import SMTPRecipientsRefused
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors
from pydantic import SecretStr

from src.core.settings import settings

logger = logging.getLogger(__name__)

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=SecretStr(settings.MAIL_PASSWORD),
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_STARTTLS=settings.MAIL_START_TLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
)


# Email for the logs without the personal data: "ana@test.dev" -> "a***@test.dev"
def _mask_email(email: str) -> str:
    name, at, domain = email.partition("@")
    return f"{name[:1]}***{at}{domain}" if at else "***"


# Runs as a background task, after the response: errors are logged, not raised (nobody would catch them)
async def send_email(subject: str, recipients: list[str], body: str) -> None:
    masked = [_mask_email(recipient) for recipient in recipients]

    try:
        message = MessageSchema.model_validate({
            "subject": subject,
            "recipients": recipients,
            "body": body,
            "subtype": MessageType.html,
        })
        await FastMail(conf).send_message(message)

    except ConnectionErrors as exc:
        # SMTP server unreachable, wrong credentials, TLS/port mismatch...
        logger.error(
            "Could not connect to the mail server: %s",
            exc,
            extra={"server": settings.MAIL_SERVER, "port": settings.MAIL_PORT, "subject": subject},
        )
        return

    except SMTPRecipientsRefused as exc:
        # The server rejected the recipients (550 user unknown...): the SMTP codes, the addresses masked
        logger.error(
            "Mail server refused the recipients",
            extra={"recipients": masked, "codes": [refused.code for refused in exc.recipients], "subject": subject},
        )
        return

    except Exception as exc:
        # No traceback: the messages of the SMTP errors carry the plain recipient
        logger.error(
            "Failed to send email: %s",
            type(exc).__name__,
            extra={"recipients": masked, "subject": subject},
        )
        return

    logger.info("Email sent", extra={"recipients": masked, "subject": subject})
