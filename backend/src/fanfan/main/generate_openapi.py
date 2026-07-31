import json

from fastapi import FastAPI

from fanfan.common.paths import SHARED_OPENAPI_PATH
from fanfan.common.version import APP_VERSION
from fanfan.presentation.web.error_codes import client_facing_error_codes
from fanfan.presentation.web.openapi import API_TITLE, generate_operation_id
from fanfan.presentation.web.routes import setup_api_router

OPENAPI_PATH = SHARED_OPENAPI_PATH


def build_openapi_schema(version: str = APP_VERSION) -> dict:
    # Mirror the runtime app's title, version and operationId scheme so the
    # committed spec matches what create_app() serves.
    app = FastAPI(
        title=API_TITLE,
        version=version,
        generate_unique_id_function=generate_operation_id,
    )
    app.include_router(setup_api_router())
    return app.openapi()


def _stamp_error_code_enum(schema: dict) -> None:
    """Expose the closed set of error codes on ErrorMessage.code as an enum.

    The model keeps `code: str` at runtime (so an unexpected code never breaks
    serialization); we add the enum to the generated spec only, so the frontend
    gets a typed union and can verify its error copy covers every code.
    """
    error_message = schema.get("components", {}).get("schemas", {}).get("ErrorMessage")
    if error_message is None:
        msg = "ErrorMessage schema missing from OpenAPI output"
        raise RuntimeError(msg)
    error_message["properties"]["code"]["enum"] = sorted(client_facing_error_codes())


def render_openapi_document(version: str = APP_VERSION) -> str:
    """Build the spec and render exactly the bytes the committed file holds.

    Serialization lives here rather than inline in main() so the drift test
    (tests/unit/presentation/test_openapi_spec.py) compares against this
    function instead of restating the json.dumps arguments — a restatement
    would drift from the writer on its own and pass while the file is stale.

    `version` is overridable for that same test. APP_VERSION reads the version
    off the *installed* distribution, so a stale editable install makes it
    disagree with pyproject.toml and every byte-comparison fail on a field that
    has not really drifted. The test therefore renders with the version the
    committed file already carries and checks that field separately, against
    pyproject.toml — which no environment can make stale.
    """
    schema = build_openapi_schema(version=version)
    _stamp_error_code_enum(schema)
    return json.dumps(schema, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    OPENAPI_PATH.parent.mkdir(parents=True, exist_ok=True)
    OPENAPI_PATH.write_text(render_openapi_document(), encoding="utf-8")


if __name__ == "__main__":
    main()
