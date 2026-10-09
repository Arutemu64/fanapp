from importlib.metadata import version
from pathlib import Path

from fanfan.common.paths import BUILD_ID_PATH

# The release version of the whole repo — frontend included — not just the
# backend. pyproject.toml holds the number (it is the only manifest that must
# carry a version and can be read back at runtime), and the `vX.Y.Z` git tag
# mirrors it. Reading it from the installed distribution rather than restating
# it here is what stops the two from drifting apart.
APP_VERSION = version("fanfan")


def read_build_id(path: Path) -> str | None:
    try:
        build_id = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return build_id or None


# The identity of a running deploy: the commit SHA the image was built from,
# baked in by the Dockerfile. None when running from source or from a local
# image build — the honest answer for a build with no published identity.
# See docs/dependencies.md for how the two are used.
APP_BUILD = read_build_id(BUILD_ID_PATH)
