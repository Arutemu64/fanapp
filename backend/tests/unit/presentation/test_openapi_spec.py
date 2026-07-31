import difflib
import json
import tomllib

import pytest

from fanfan.common.paths import BACKEND_DIR, SHARED_OPENAPI_PATH
from fanfan.main.generate_openapi import render_openapi_document

pytestmark = pytest.mark.unit

PYPROJECT_PATH = BACKEND_DIR / "pyproject.toml"

# A full diff of a spec this size buries the signal; the first hunks are enough
# to name the endpoint or schema that moved.
MAX_DIFF_LINES = 40

DRIFT_MESSAGE = """\
shared/openapi/openapi.json is out of date with the routers and DTOs.

Regenerate it (and the frontend types built from it) with:
    just frontend-generate-api

First {shown} diff lines (committed -> generated):
{diff}"""


def committed_spec() -> dict:
    return json.loads(SHARED_OPENAPI_PATH.read_text(encoding="utf-8"))


def test_committed_spec_matches_the_code() -> None:
    """Fail if the committed OpenAPI spec drifts from the code that generates it.

    The spec feeds frontend/src/lib/api/schema.d.ts, which in turn feeds the
    compile-time guards in lib/api/errors.ts and lib/utils/permissions.ts
    (docs/api.md). A stale spec is internally consistent, so `pnpm check` stays
    green while those guards compare the frontend against a contract the backend
    no longer serves. This test is what keeps them anchored to the backend.

    Everything except `info.version` is compared byte for byte, formatting
    included, so the committed file is exactly what the generator writes. The
    version is environment-dependent and gets its own test below.
    """
    committed_text = SHARED_OPENAPI_PATH.read_text(encoding="utf-8")
    generated = render_openapi_document(
        version=committed_spec()["info"]["version"],
    )

    if committed_text == generated:
        return

    diff = list(
        difflib.unified_diff(
            committed_text.splitlines(),
            generated.splitlines(),
            fromfile="committed",
            tofile="generated",
            lineterm="",
        )
    )
    shown = diff[:MAX_DIFF_LINES]
    pytest.fail(
        DRIFT_MESSAGE.format(shown=len(shown), diff="\n".join(shown)),
        pytrace=False,
    )


def test_committed_spec_version_matches_pyproject() -> None:
    """Fail if the spec was not regenerated after a release version bump.

    Deliberately compares two *committed* files rather than reading
    APP_VERSION: the runtime value comes from the installed distribution
    metadata, so a stale editable install would fail this for a spec that is
    perfectly correct. Both inputs here are in the repo, so the result is the
    same on a laptop, in CI, and in a cloud session.
    """
    pyproject = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))

    assert committed_spec()["info"]["version"] == pyproject["project"]["version"], (
        "shared/openapi/openapi.json carries a different version than "
        "backend/pyproject.toml. A version bump has to regenerate the spec:\n"
        "    just backend-generate-openapi\n"
        "If you just regenerated and this still fails, the installed "
        "distribution is stale (APP_VERSION reads it, not pyproject.toml) — "
        "run `uv sync` in backend/ and regenerate again."
    )
