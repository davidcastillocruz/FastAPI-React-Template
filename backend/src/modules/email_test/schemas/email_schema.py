"""
Request schema for the email endpoint.

Validates the incoming `email` field using `email-validator`, but
raises a project-specific `PydanticCustomError` with the code
`"INVALID_EMAIL"` instead of the library's default message. That code
is later resolved by the validation exception handler in `main.py`,
which maps it to the translated message from `language_responses.json`.
"""

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, field_validator
from pydantic_core import PydanticCustomError


class EmailSchema(BaseModel):
    """Payload accepted by the email request endpoint.

    The `email` field is validated with `email-validator`. On failure,
    a `PydanticCustomError` with type `"INVALID_EMAIL"` is raised. The
    handler in `main.py` reads that type and returns the translated
    message, so this schema does not need access to the request or to
    the language manager.
    """

    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate the email format and raise `INVALID_EMAIL` on failure.

        Uses `check_deliverability=False` so no DNS lookup is performed.
        Only the syntax is validated, which is what we want: the caller
        is responsible for the address actually existing.

        Args:
            v: Raw email string provided by the client.

        Returns:
            The email string, unchanged, if it is syntactically valid.

        Raises:
            PydanticCustomError: With type `"INVALID_EMAIL"` if the
                string is not a valid email address.
        """
        try:
            validate_email(v, check_deliverability=False)
        except EmailNotValidError:
            raise PydanticCustomError(
                "INVALID_EMAIL",
                "",
            )
        return v