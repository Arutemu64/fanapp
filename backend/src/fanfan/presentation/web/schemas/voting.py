from typing import Self

from pydantic import MISSING, model_validator

from fanfan.application.dto.input import InputModel


class UpdateNominationBody(InputModel):
    is_votable: bool | MISSING = MISSING

    # An empty patch would answer 204 without reaching the interactor's
    # access and existence checks.
    @model_validator(mode="after")
    def _some_change(self) -> Self:
        if not self.model_fields_set:
            msg = "Send at least one field to change"
            raise ValueError(msg)
        return self
