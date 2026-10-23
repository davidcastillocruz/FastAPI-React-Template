import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


# Body with only an email, like POST /email-requests
class EmailSchema(BaseModel):
    email: EmailStr

    # "Ana@Test.dev" and "ana@test.dev" are the same email: it is saved and looked up in lowercase
    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


# One email request in GET /email-requests, built from the database model
class EmailRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    created_at: datetime
