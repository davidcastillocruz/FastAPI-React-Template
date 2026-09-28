"""
Data-access layer for `EmailRequestModel`.

This module only performs database operations: no business logic, no
HTTP concerns, no translation. It is the boundary between the service
layer and the database, and it never makes decisions about what to do
with the results — it only returns them (or raises) to the caller.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logger import get_logger
from src.modules.email_test.models.email_request_model import EmailRequestModel

logger = get_logger(__name__)


async def get_email_request_db(
    db: AsyncSession,
    email: str,
) -> EmailRequestModel | None:
    """Fetch an email request by its email address.

    Args:
        db: Active async database session.
        email: Email address to look up.

    Returns:
        The matching `EmailRequestModel`, or `None` if no row exists.

    Raises:
        Exception: Any error raised by the database driver is logged
            and re-raised so the caller can decide how to handle it.
    """
    try:
        result = await db.execute(
            select(EmailRequestModel).where(EmailRequestModel.email == email)
        )
        email_request = result.scalar_one_or_none()

        if email_request:
            logger.debug("EMAIL_REQUEST_FOUND", email=email)
        else:
            logger.debug("EMAIL_REQUEST_NOT_FOUND", email=email)

        return email_request
    except Exception:
        logger.exception("ERROR_GETTING_EMAIL_REQUEST", email=email)
        raise


async def create_email_request_db(db: AsyncSession, email: str) -> None:
    """Insert a new email request.

    On any failure, rolls back the current transaction before
    re-raising. This matters for the unique constraint on `email`:
    without a rollback, the session would remain in a broken state and
    subsequent queries would fail.

    Args:
        db: Active async database session.
        email: Email address to insert.

    Raises:
        IntegrityError: If the email already exists (unique constraint).
        Exception: Any other database error is logged and re-raised.
    """
    try:
        new_email_request = EmailRequestModel(email=email)
        db.add(new_email_request)
        await db.commit()
        logger.debug("EMAIL_REQUEST_CREATED", email=email)
    except Exception:
        await db.rollback()
        logger.exception("ERROR_CREATING_EMAIL_REQUEST", email=email)
        raise