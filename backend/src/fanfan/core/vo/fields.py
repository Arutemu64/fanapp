from pydantic import Field

USERNAME_PATTERN = r"^[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9_]{2,24}$"

USERNAME_FIELD = Field(
    min_length=3,
    max_length=25,
    pattern=USERNAME_PATTERN,
)
PASSWORD_MAX_LENGTH = 128

PASSWORD_FIELD = Field(
    min_length=10,
    max_length=PASSWORD_MAX_LENGTH,
    repr=False,
)
