from pydantic import BaseModel, ConfigDict


class InputModel(BaseModel):
    """Base of every model a client sends: a request body, form or query.

    An unknown field is a 422 rather than silently ignored, so a misspelled
    PATCH field can't answer 204 and change nothing. Webhook payloads stay
    plain `BaseModel`s: the vendor adds fields without telling us.
    """

    model_config = ConfigDict(extra="forbid")
