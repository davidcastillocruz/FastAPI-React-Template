"""
Business logic for the email request endpoint.

Coordinates three layers:

- **Repository** (`email_request_repository`): database access.
- **Schema** (`email_schema`): input validation, performed by FastAPI
  before this function is called.
- **Language manager** (`language_manager`): translated responses and
  exceptions, resolved from the request language.

The service decides the order of operations and turns infrastructure
errors (unique constraint, SMTP failures) into responses or
`HTTPException`s with translated payloads. It does not touch the
database directly, nor does it know anything about SQLAlchemy beyond
the `IntegrityError` it catches.
"""

from fastapi import BackgroundTasks, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.language_manager import get_exception, get_response
from src.core.logger import get_logger
from src.core.request_utils import get_client_ip
from src.email.emails import test_email
from src.email.sender import send_email
from src.modules.email_test.repositories.email_request_repository import (
    create_email_request_db,
    get_email_request_db,
)
from src.modules.email_test.schemas.email_schema import EmailSchema

logger = get_logger(__name__)


async def create_email_request(
    request: Request,
    email_form: EmailSchema,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
) -> dict:
    """Register an email and queue a confirmation email.

    Flow:

    1. Check whether the email is already registered. If so, return the
       translated "already registered" message with a 200 status.
    2. Otherwise, insert the email. If a race condition causes the
       unique constraint to fire, return 409 with the same translated
       message.
    3. Render the confirmation email and enqueue it via
       `background_tasks`. The send runs after the response is returned
       to the client.
    4. Return the translated "registered" message.

    Args:
        request: Incoming FastAPI request, used for language resolution
            and logging context.
        email_form: Validated request payload, containing the email.
        background_tasks: FastAPI background task queue for the send.
        db: Active async database session.

    Returns:
        Translated response payload with a ``"message"`` key.

    Raises:
        HTTPException: 409 if the email is already registered due to a
            race condition between the check and the insert.
    """
    client_ip = get_client_ip(request)
    logger.info(
        "EMAIL_REQUEST_CREATION_STARTED",
        ip=client_ip,
        email=email_form.email,
    )

    # Fast path: the email is already in the database.
    email_request = await get_email_request_db(db=db, email=email_form.email)
    if email_request:
        logger.info(
            "EMAIL_ALREADY_REGISTERED",
            ip=client_ip,
            email=email_form.email,
        )
        return get_response(
            name="EMAIL_ALREADY_REGISTERED",
            request=request,
            placeholders=[{"message": email_form.email}],
        )

    # Slow path: insert. The unique constraint covers the race condition
    # between the check above and this insert.
    try:
        await create_email_request_db(db=db, email=email_form.email)
    except IntegrityError:
        logger.error(
            "EMAIL_REQUEST_CREATION_FAILED",
            ip=client_ip,
            email=email_form.email,
            reason="Email already registered",
        )
        raise HTTPException(
            status_code=409,
            detail=get_exception(
                name="EMAIL_ALREADY_REGISTERED",
                request=request,
                placeholders=[{"detail": email_form.email}],
            ),
        )

    # Render the email and enqueue the send. The actual SMTP call runs
    # after the response has been returned.
    subject, html_body, text_body = test_email.render()
    background_tasks.add_task(
        send_email,
        to=email_form.email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )

    logger.info(
        "EMAIL_REQUEST_CREATION_FINISHED",
        ip=client_ip,
        email=email_form.email,
    )
    return get_response(name="EMAIL_REGISTERED", request=request)