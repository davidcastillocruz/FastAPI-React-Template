from pydantic import BaseModel


# Response with only a translated message for the user: {"message": "..."}
class MessageResponse(BaseModel):
    message: str


# Every error of the API: {"detail": "..."} translated, see core/errors.py
class ErrorResponse(BaseModel):
    detail: str
