import json
from pathlib import Path

from fastapi import FastAPI

from fanfan.presentation.web.routes import setup_api_router

OPENAPI_PATH = (
    Path(__file__).resolve().parents[4] / "shared" / "openapi" / "openapi.json"
)


def build_openapi_schema() -> dict:
    app = FastAPI()
    app.include_router(setup_api_router())
    return app.openapi()


def main() -> None:
    OPENAPI_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema = build_openapi_schema()
    OPENAPI_PATH.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
