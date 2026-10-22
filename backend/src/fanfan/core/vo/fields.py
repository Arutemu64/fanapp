from pydantic import Field

USERNAME_PATTERN = r"^[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9_]{2,24}$"

USERNAME_FIELD = Field(
    min_length=3,
    max_length=25,
    pattern=USERNAME_PATTERN,
)
# Also caps the password a login may send: no stored password is longer, and an
# unbounded one would let a request make the hasher chew on megabytes.
PASSWORD_MAX_LENGTH = 128

# Every secret field (passwords, one-time codes) sets repr=False. A model's repr
# is what Sentry records for a frame's local variables, and its scrubber matches
# variable names, not the text of a repr, so a plain field would ship the
# password with any unexpected error. SecretStr was the alternative: it changes
# every call site to .get_secret_value() and the field's type to the type checker.
PASSWORD_FIELD = Field(
    min_length=10,
    max_length=PASSWORD_MAX_LENGTH,
    repr=False,
)
