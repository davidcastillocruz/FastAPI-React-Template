from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query, Request, status

from src.api.dependencies import Language
from src.core.limiter import limiter
from src.database.session import DbSession
from src.modules.demo.schemas.email_request_schemas import EmailRequestCreate, EmailRequestResponse
from src.modules.demo.services import email_request_service as service
from src.shared.schemas import MessageResponse

router = APIRouter(prefix="/email-requests", tags=["Email requests"])


# The limiter needs the request parameter: it reads the client IP from it
@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_email_request(
    request: Request,
    body: EmailRequestCreate,
    db: DbSession,
    language: Language,
    background_tasks: BackgroundTasks,
) -> MessageResponse:
    return await service.create_email_request(db, body.email, language, background_tasks)


# ?page=1 is the first page. le: a huge page would overflow the offset in Postgres (a 500),
# 100_000 pages of 10 is far beyond any real use
@router.get("")
async def get_email_requests(
    db: DbSession,
    page: Annotated[int, Query(ge=1, le=100_000)] = 1,
) -> list[EmailRequestResponse]:
    return await service.get_email_requests(db, page)
