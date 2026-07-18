import tempfile
from pathlib import Path

# Single source of truth for filesystem anchors. All parent-hop counting happens
# HERE so other modules import a named constant instead of re-deriving
# `Path(__file__).resolve().parents[N]` with a magic N that breaks silently when
# a file moves. .resolve() first so symlinks and `..` collapse before we walk up.
# This file lives at backend/src/fanfan/common/paths.py.
_THIS_FILE = Path(__file__).resolve()

SRC_DIR = _THIS_FILE.parents[2]  # backend/src
APP_DIR = SRC_DIR / "fanfan"
BACKEND_DIR = SRC_DIR.parent  # backend
REPO_ROOT = BACKEND_DIR.parent  # repo root

COMMON_STATIC_DIR = _THIS_FILE.parent / "static"

# Repo-root-relative anchors shared by the CLI generators and bootstrap tooling.
SECRETS_DIR = REPO_ROOT / "secrets"
SHARED_OPENAPI_PATH = REPO_ROOT / "shared" / "openapi" / "openapi.json"

TEMP_DIR = Path(tempfile.gettempdir())
TEMP_DIR.mkdir(parents=True, exist_ok=True)

QR_CODES_TEMP_DIR = TEMP_DIR.joinpath("qr_codes")
QR_CODES_TEMP_DIR.mkdir(parents=True, exist_ok=True)
