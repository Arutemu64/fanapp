from pathlib import Path

from pydantic import BaseModel


class PushConfig(BaseModel):
    private_key_path: Path
    public_key_path: Path
    subscriber: str
