def normalize_email(email: str) -> str:
    """Normalize email addresses before storing or comparing them."""

    return email.strip().lower()