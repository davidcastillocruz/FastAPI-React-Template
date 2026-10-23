from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.demo.models.email_request_model import EmailRequest

# No commit and no rollback here: the service commits once, at the end of its flow.
# On any error the request ends and closing the session (get_db) rolls it back


# The email must come lowercased, as it is saved (EmailSchema already does it)
async def get_email_request_by_email(db: AsyncSession, email: str) -> EmailRequest | None:
    return await db.scalar(select(EmailRequest).where(EmailRequest.email == email))


# New email request, the email must come lowercased. The flush gives it its id, and a repeated email fails here
async def create_email_request(db: AsyncSession, email: str) -> EmailRequest:
    email_request = EmailRequest(email=email)
    db.add(email_request)
    await db.flush()
    return email_request


# Newest first, id breaks ties so the same rows always give the same pages
# (a row saved between two page loads moves the next page one row)
async def get_email_requests(db: AsyncSession, offset: int, limit: int) -> list[EmailRequest]:
    query = (
        select(EmailRequest)
        .order_by(EmailRequest.created_at.desc(), EmailRequest.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(await db.scalars(query))
