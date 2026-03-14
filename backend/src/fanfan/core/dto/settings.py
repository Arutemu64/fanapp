from pydantic import BaseModel, ConfigDict, Field


class LimitsConfigDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # Keep the validation rule close to the schema so OpenAPI documents it too.
    announcement_timeout: int = Field(ge=1)


class AppSettingsDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    voting_enabled: bool
    limits: LimitsConfigDTO
