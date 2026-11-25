from pydantic import BaseModel


class Ticket(BaseModel, frozen=True):
    id: str
    barcode: str | None
