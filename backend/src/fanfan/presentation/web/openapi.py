from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute

# FastAPI's default title is the literal "FastAPI", which names the framework
# rather than the service — misleading in the committed spec and in anything
# rendered from it (/docs, generated clients). Set at every FastAPI build site
# for the same reason as generate_operation_id below.
API_TITLE = "FAN FAN API"


def generate_operation_id(route: APIRoute) -> str:
    """Use the endpoint function name as the OpenAPI operationId.

    The FastAPI default appends the path and method (e.g.
    ``get_schedule_schedule__get``), which produces noisy type names in the
    generated frontend client. Endpoint
    function names are already unique across our routers, so the bare name is a
    clean, stable id. Applied at every FastAPI build site (runtime app and the
    spec generator) so the committed spec matches what the app serves.
    """
    return route.name


def drop_unreachable_validation_responses(schema: dict[str, Any]) -> None:
    """Remove the 422 response from operations that take no input.

    setup_api_router() attaches VALIDATION_RESPONSES to every router, so it also
    lands on operations with no parameters and no body, which can never fail
    request validation. On the SSE stream it would also be wrong: FastAPI gives
    an additional response the route's own media type, so the JSON error body
    would be advertised as text/event-stream. FastAPI's built-in 422 applies this
    same no-input test, but documents its own HTTPValidationError shape rather
    than our ValidationErrorResponse, which is why the 422 is ours to prune.
    """
    for path_item in schema["paths"].values():
        for operation in path_item.values():
            takes_input = "parameters" in operation or "requestBody" in operation
            if not takes_input:
                operation["responses"].pop("422", None)


class FanfanAPI(FastAPI):
    """FastAPI whose schema goes through drop_unreachable_validation_responses.

    Overrides the hook FastAPI's "Extending OpenAPI" guide points at; used at
    every build site so /openapi.json matches the committed spec.
    """

    def openapi(self) -> dict[str, Any]:
        if self.openapi_schema is not None:
            return self.openapi_schema
        schema = super().openapi()
        drop_unreachable_validation_responses(schema)
        return schema
