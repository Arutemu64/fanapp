from typing import ClassVar

from pydantic import BaseModel


class AppEvent(BaseModel):
    # Names the event in the jobs table and in the worker's routing table.
    subject: ClassVar[str]
