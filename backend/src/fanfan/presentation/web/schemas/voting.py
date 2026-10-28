from pydantic import MISSING

from fanfan.application.dto.input import InputModel


class UpdateNominationBody(InputModel):
    is_votable: bool | MISSING = MISSING
