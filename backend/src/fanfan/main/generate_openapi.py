import json
from pathlib import Path

from fastapi import FastAPI

from fanfan.presentation.web.error_codes import client_facing_error_codes
from fanfan.presentation.web.routes import setup_api_router

OPENAPI_PATH = (
    Path(__file__).resolve().parents[4] / "shared" / "openapi" / "openapi.json"
)


def build_openapi_schema() -> dict:
    app = FastAPI()
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
