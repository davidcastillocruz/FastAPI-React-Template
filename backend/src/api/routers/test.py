"""HTTP routes for the email request module."""

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.modules.email_test.schemas.email_schema import EmailSchema
from src.modules.email_test.services.email_test_service import create_email_request

router = APIRouter()


@router.post("/email-request")
async def post_email_request(
    request: Request,
    email_form: EmailSchema,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Register a new email request and queue a confirmation email.

    Thin route: wires dependencies (DB session, background tasks, request
    context) and delegates the business logic to `create_email_request`.
    """
    return await create_email_request(
        request=request,
        email_form=email_form,
        background_tasks=background_tasks,
        db=db,
    )