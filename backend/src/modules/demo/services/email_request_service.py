import logging

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.languages import get_error_detail, get_response
from src.mail.sender import send_email
from src.mail.templates.demo_email import build_demo_email
from src.modules.demo.repositories import email_request_repository
from src.modules.demo.schemas.email_request_schemas import EmailRequestResponse, EmailSchema
from src.shared.schemas import MessageResponse

logger = logging.getLogger(__name__)

# Rows of each page of GET /email-requests
PAGE_SIZE = 10


# 409 when the email has already asked for a test email
def _already_requested(language: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=get_error_detail("EMAIL_ALREADY_REQUESTED", language),
    )


# Saves the email and sends it a test email after the response
async def create_email_request(
    db: AsyncSession,
    body: EmailSchema,
    language: str,
    background_tasks: BackgroundTasks,
) -> MessageResponse:
    if await email_request_repository.get_email_request_by_email(db, body.email):
        raise _already_requested(language)

    # Built before saving: if a text is missing the request fails without leaving a saved email behind
    subject, html = build_demo_email(language)

    try:
        email_request = await email_request_repository.create_email_request(db, body.email)
    except IntegrityError:
        # Two requests with the same email at the same time: the unique constraint stops the second one
        raise _already_requested(language) from None
    await db.commit()
    logger.info("Email request saved", extra={"email_request_id": email_request.id})

    background_tasks.add_task(send_email, subject, [body.email], html)
    return MessageResponse(**get_response("EMAIL_REQUEST_CREATED", language))


# One page of email requests, page 1 is the first one
async def get_email_requests(db: AsyncSession, page: int) -> list[EmailRequestResponse]:
    offset = (page - 1) * PAGE_SIZE
    email_requests = await email_request_repository.get_email_requests(db, offset, PAGE_SIZE)
    return [EmailRequestResponse.model_validate(email_request) for email_request in email_requests]
