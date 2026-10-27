import tempfile
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()

SRC_DIR = _THIS_FILE.parents[2]
APP_DIR = SRC_DIR / "fanfan"
BACKEND_DIR = SRC_DIR.parent
REPO_ROOT = BACKEND_DIR.parent

BUILD_ID_PATH = BACKEND_DIR / "BUILD_ID"

COMMON_STATIC_DIR = _THIS_FILE.parent / "static"

SECRETS_DIR = REPO_ROOT / "secrets"
SHARED_OPENAPI_PATH = REPO_ROOT / "shared" / "openapi" / "openapi.json"

TEMP_DIR = Path(tempfile.gettempdir())
TEMP_DIR.mkdir(parents=True, exist_ok=True)

QR_CODES_TEMP_DIR = TEMP_DIR.joinpath("qr_codes")
QR_CODES_TEMP_DIR.mkdir(parents=True, exist_ok=True)
