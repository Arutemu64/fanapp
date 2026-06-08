import secrets

EMAIL_LOGIN_CODE_MAX_AGE_SECONDS = 900
EMAIL_CONFIRMATION_CODE_MAX_AGE_SECONDS = 3600
EMAIL_OTP_LENGTH = 6
EMAIL_CODE_REQUEST_COOLDOWN_SECONDS = 60
# How many wrong code guesses a target may make within EMAIL_OTP_LOCKOUT_SECONDS
# before it is locked out. Caps brute-force of the 6-digit code.
EMAIL_OTP_MAX_ATTEMPTS = 5
# How long a target stays locked out after using up its guesses. Kept short so
# a user who fat-fingers the code is not blocked for the code's whole lifetime.
EMAIL_OTP_LOCKOUT_SECONDS = 900


def generate_numeric_code() -> str:
    # Keep the code short enough for mobile input, but still random.
    return f"{secrets.randbelow(10**EMAIL_OTP_LENGTH):0{EMAIL_OTP_LENGTH}d}"
