from pathlib import Path

from pydantic import BaseModel, field_validator

# Go up 5 levels from: backend/src/fanfan/adapters/push/config.py -> backend/src/fanfan/adapters/ -> backend/src/fanfan/ -> backend/src/ -> backend/ -> fanapp/
PROJECT_ROOT = Path(__file__).resolve().parents[5]


class PushConfig(BaseModel):
    # Generate a private/public pair of VAPID keys
    # using `vapid-gen` and put them into config
    # directory in the root
    private_key_path: Path
    public_key_path: Path

    # Claims email
    subscriber: str

    @field_validator("private_key_path", "public_key_path", mode="after")
    @classmethod
    def resolve_relative_path(cls, v: Path) -> Path:
        # If the path is not absolute, resolve it against the project root
        if not v.is_absolute():
            return (PROJECT_ROOT / v).resolve()
        return v

