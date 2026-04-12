import re

from sqlalchemy.exc import IntegrityError


def get_constraint_name(error: IntegrityError) -> str | None:
    """Extract DB constraint name from SQLAlchemy integrity errors.

    Works with asyncpg errors and keeps a string fallback for other drivers.
    """

    original_error = error.orig
    constraint_name = getattr(original_error, "constraint_name", None)
    if constraint_name:
        return constraint_name

    diagnostic = getattr(original_error, "diag", None)
    if diagnostic:
        constraint_name = getattr(diagnostic, "constraint_name", None)
        if constraint_name:
            return constraint_name

    match = re.search(r'constraint\s+"([^"]+)"', str(original_error), re.IGNORECASE)
    if match:
        return match.group(1)

    return None
