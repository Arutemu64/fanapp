from typing import ClassVar

from pydantic import BaseModel


class AppEvent(BaseModel):
    subject: ClassVar[str]
