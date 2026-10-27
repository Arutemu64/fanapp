from datetime import timedelta
from typing import Any

from sqlalchemy import ColumnElement, func


def expires_in(seconds: int) -> ColumnElement[Any]:
    """An ``expires_at`` value on the database clock, at least one second out."""
    return func.now() + timedelta(seconds=max(1, seconds))
