from pathlib import Path

from pydantic import BaseModel


class PushConfig(BaseModel):
    # Generate a private/public pair of VAPID keys with
    # `just backend-generate-vapid` (or `just bootstrap`); they land in the
    # `secrets/` directory at the repo root.
    private_key_path: Path
    public_key_path: Path

    # VAPID "sub" claim — a mailto/contact address for the push service.
    subscriber: str
