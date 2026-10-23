from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


# Body of POST /email-requests
class EmailRequestCreate(BaseModel):
    email: EmailStr


# One email request in GET /email-requests, built from the database model
class EmailRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime
