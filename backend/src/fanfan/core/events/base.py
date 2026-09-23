from typing import ClassVar

from pydantic import BaseModel


class AppEvent(BaseModel):
    subject: ClassVar[str]

    def dedup_id(self) -> str | None:
        """A stable id for this event, if it has one.

        An event republished with the same id — a redelivered trigger rerunning
        its fan-out — is dropped by the broker inside its dedup window. Events
        without a natural identity return None and are never deduplicated.
        """
        return None
