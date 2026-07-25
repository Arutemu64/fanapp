import json

from fastapi import FastAPI

from fanfan.common.paths import SHARED_OPENAPI_PATH
from fanfan.common.version import APP_VERSION
from fanfan.presentation.web.error_codes import client_facing_error_codes
from fanfan.presentation.web.openapi import API_TITLE, generate_operation_id
from fanfan.presentation.web.routes import setup_api_router

OPENAPI_PATH = SHARED_OPENAPI_PATH


def build_openapi_schema() -> dict:
    # Mirror the runtime app's title, version and operationId scheme so the
    # committed spec matches what create_app() serves.
    app = FastAPI(
        title=API_TITLE,
        version=APP_VERSION,
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


def main() -> None:
    OPENAPI_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema = build_openapi_schema()
    _stamp_error_code_enum(schema)
    OPENAPI_PATH.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
