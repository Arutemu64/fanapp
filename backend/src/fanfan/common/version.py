from importlib.metadata import version
from pathlib import Path

from fanfan.common.paths import BUILD_ID_PATH

APP_VERSION = version("fanfan")


def read_build_id(path: Path) -> str | None:
    try:
        build_id = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return build_id or None


APP_BUILD = read_build_id(BUILD_ID_PATH)
