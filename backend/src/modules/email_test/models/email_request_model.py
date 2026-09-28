"""
SQLAlchemy model for the `email_requests` table.

Stores one row per email that has requested an action from the API
(currently, a confirmation email). The `email` column is unique, so
duplicate requests are rejected at the database level and surface as
`IntegrityError` — see `email_request_repository.create_email_request_db`.
"""

from sqlalchemy import Column, Integer, String

from src.database.base import Base


class EmailRequestModel(Base):
    """A registered email request.

    Attributes:
        id: Auto-incremented primary key.
        email: The email address. Unique and indexed. Length is capped
            at 255 characters, which matches the RFC 5321 limit for the
            total address length.
    """

    __tablename__ = "email_requests"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)