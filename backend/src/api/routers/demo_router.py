from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query, Request, status

from src.api.dependencies import Language
from src.core.limiter import EMAIL_LIMIT, READ_LIMIT, limiter
from src.database.session import DbSession
from src.modules.demo.schemas.email_request_schemas import EmailRequestResponse, EmailSchema
from src.modules.demo.services import email_request_service
from src.shared.schemas import MessageResponse

router = APIRouter(prefix="/email-requests", tags=["Email requests"])


# Saves an email and sends it the test email. The limiter needs the request parameter: it reads the client IP from it
@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit(EMAIL_LIMIT)
async def create_email_request(
    request: Request,
    body: EmailSchema,
    db: DbSession,
    language: Language,
    background_tasks: BackgroundTasks,
) -> MessageResponse:
    return await email_request_service.create_email_request(db, body, language, background_tasks)


# A page of the departures board, ?page=1 is the first one. le: a huge page would overflow the offset in Postgres
# (a 500), 100_000 pages of 10 is far beyond any real use
@router.get("")
@limiter.limit(READ_LIMIT)
async def get_email_requests(
    request: Request,
    db: DbSession,
    page: Annotated[int, Query(ge=1, le=100_000)] = 1,
) -> list[EmailRequestResponse]:
    return await email_request_service.get_email_requests(db, page)
