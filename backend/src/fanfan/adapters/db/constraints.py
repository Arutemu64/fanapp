import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager

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


@contextmanager
def translate_integrity_error(
    mapping: Mapping[str, type[Exception]],
) -> Iterator[None]:
    """Map a DB constraint violation to a domain exception.

    On IntegrityError, look up the violated constraint name and raise the
    matching domain exception. Unmapped constraints are re-raised unchanged,
    so an unexpected violation (a NOT NULL or CHECK bug) is never silently
    swallowed or mislabeled.

    Wrap the write that can violate a constraint, e.g.::

        with translate_integrity_error({"uq_votes_user_id": VoteAlreadyExists}):
            self.session.add(vote_orm)
            await self.session.flush([vote_orm])
    """
    try:
        yield
    except IntegrityError as e:
        constraint_name = get_constraint_name(e)
        exception = mapping.get(constraint_name) if constraint_name else None
        if exception is not None:
            raise exception from e
        raise
