import secrets
from typing import NewType
from uuid import UUID, uuid7

TicketId = NewType("TicketId", UUID)

# Human-friendly Crockford Base32 alphabet: the digits 0-9 plus the 22 letters
# that remain after excluding I, L, O (confusable with 1/0) and U (avoids
# accidental obscenity). Codes are read aloud, typed and copied by a non-tech
# audience, so an unambiguous, case-insensitive alphabet matters more than the
# extra couple of symbols a full Base32 would add.
# See http://www.crockford.com/base32.html
_CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_BARCODE_PREFIX = "FAN-"
_BARCODE_BODY_LENGTH = 6


def generate_ticket_id() -> TicketId:
    return TicketId(uuid7())


def generate_ticket_barcode() -> str:
    """Return a fresh barcode like ``FAN-7K4Q9M`` for an org-issued ticket.

    The ``FAN-`` prefix keeps generated tickets visibly distinct from imported
    vendor barcodes; uniqueness is ultimately enforced by the DB constraint, so
    callers must be ready to regenerate on the (astronomically rare) collision.
    """
    body = "".join(
        secrets.choice(_CROCKFORD_ALPHABET) for _ in range(_BARCODE_BODY_LENGTH)
    )
    return f"{_BARCODE_PREFIX}{body}"
