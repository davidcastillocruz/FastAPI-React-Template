from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query, Request, status

from src.api.dependencies import Language
from src.core.limiter import limiter
from src.database.session import DbSession
from src.modules.demo.schemas.email_request_schemas import EmailRequestResponse, EmailSchema
from src.modules.demo.services import email_request_service
from src.shared.schemas import MessageResponse

router = APIRouter(prefix="/email-requests", tags=["Email requests"])


# Each request sends a real email: a few per minute, and a limit per day for what stays below it.
# The limiter needs the request parameter: it reads the client IP from it
@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute;50/day")
async def create_email_request(
    request: Request,
    body: EmailSchema,
    db: DbSession,
    language: Language,
    background_tasks: BackgroundTasks,
) -> MessageResponse:
    return await email_request_service.create_email_request(db, body, language, background_tasks)


# A read that goes through the pages of the board: higher than the limit of what sends emails.
# ?page=1 is the first page. le: a huge page would overflow the offset in Postgres (a 500),
# 100_000 pages of 10 is far beyond any real use
@router.get("")
@limiter.limit("60/minute;2000/day")
async def get_email_requests(
    request: Request,
    db: DbSession,
    page: Annotated[int, Query(ge=1, le=100_000)] = 1,
) -> list[EmailRequestResponse]:
    return await email_request_service.get_email_requests(db, page)
