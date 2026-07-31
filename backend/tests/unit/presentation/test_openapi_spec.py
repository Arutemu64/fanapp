import difflib

import pytest

from fanfan.common.paths import SHARED_OPENAPI_PATH
from fanfan.main.generate_openapi import render_openapi_document

pytestmark = pytest.mark.unit

# A full diff of a spec this size buries the signal; the first hunks are enough
# to name the endpoint or schema that moved.
MAX_DIFF_LINES = 40

DRIFT_MESSAGE = """\
shared/openapi/openapi.json is out of date with the routers and DTOs.

Regenerate it (and the frontend types built from it) with:
    just frontend-generate-api

If the only difference is info.version, the spec is fine and the installed
distribution metadata is stale — APP_VERSION reads it, not pyproject.toml.
Run `uv sync` in backend/ and re-run this test.

First {shown} diff lines (committed -> generated):
{diff}"""


def test_committed_spec_matches_the_code() -> None:
    """Fail if the committed OpenAPI spec drifts from the code that generates it.

    The spec feeds frontend/src/lib/api/schema.d.ts, which in turn feeds the
    compile-time guards in lib/api/errors.ts and lib/utils/permissions.ts
    (docs/api.md). A stale spec is internally consistent, so `pnpm check` stays
    green while those guards compare the frontend against a contract the backend
    no longer serves. This test is what keeps them anchored to the backend.
    """
    generated = render_openapi_document()
    committed = SHARED_OPENAPI_PATH.read_text(encoding="utf-8")

    if committed == generated:
        return

    diff = list(
        difflib.unified_diff(
            committed.splitlines(),
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
