from pathlib import Path

from pydantic import BaseModel


class PushConfig(BaseModel):
    # Generate a private/public pair of VAPID keys
    # using `vapid-gen` and put them into config
    # directory in the root
    private_key_path: Path
    public_key_path: Path

    # Claims email
    subscriber: str
