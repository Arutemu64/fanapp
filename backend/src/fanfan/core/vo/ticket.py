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
# Crockford decoding reads the excluded look-alikes as the digits they resemble.
_CROCKFORD_CONFUSABLES = str.maketrans({"I": "1", "L": "1", "O": "0"})


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


def normalize_ticket_barcode(raw: str) -> str:
    """Return the stored form of a barcode as a person typed it.

    Org-issued ``FAN-`` codes are Crockford Base32, which is case-insensitive
    and forgiving of I/L/O by design — a phone keyboard types them in lowercase,
    and the lookup is an exact match. Other barcodes keep their exact spelling:
    an imported vendor format is not ours to fold. A vendor code could still
    start with ``FAN-``, so look up the exact spelling before this folded form.
    """
    barcode = raw.strip()
    if not barcode.upper().startswith(_BARCODE_PREFIX):
        return barcode
    body = barcode[len(_BARCODE_PREFIX) :].upper().translate(_CROCKFORD_CONFUSABLES)
    return f"{_BARCODE_PREFIX}{body}"
