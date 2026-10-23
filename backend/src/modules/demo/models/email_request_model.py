import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


# Database model of the email requests of the demo
class EmailRequest(Base):
    __tablename__ = "email_requests"

    # The database generates the id: rows created outside the app (a script, a seed) get one too
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
