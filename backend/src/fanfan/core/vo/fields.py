from pydantic import Field

USERNAME_FIELD = Field(
    ...,
    min_length=3,
    max_length=20,
    pattern=r"^[a-zA-Z0-9_-]+$",
)
PASSWORD_FIELD = Field(
    ...,
    min_length=8,
    max_length=128,
)
