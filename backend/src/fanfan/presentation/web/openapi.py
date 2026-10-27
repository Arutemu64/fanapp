from collections.abc import Iterator
from typing import Any, override

from fastapi import FastAPI
from fastapi.routing import APIRoute
from pydantic import TypeAdapter

from fanfan.application.dto.realtime import SSEEventName
from fanfan.presentation.web.schemas.error import PROBLEM_JSON_MEDIA_TYPE

API_TITLE = "FAN FAN API"
SSE_PATH = "/events"
SSE_MEDIA_TYPE = "text/event-stream"


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


def iter_operations(schema: dict[str, Any]) -> Iterator[dict[str, Any]]:
    for path_item in schema["paths"].values():
        yield from path_item.values()


def iter_responses(schema: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    for operation in iter_operations(schema):
        yield from operation["responses"].items()


def drop_unreachable_validation_responses(schema: dict[str, Any]) -> None:
    """Remove the 422 response from operations that take no input.

    setup_api_router() attaches VALIDATION_RESPONSES to every router, so it also
    lands on operations with no parameters and no body, which can never fail
    request validation. On the SSE stream it would also be wrong: FastAPI gives
    an additional response the route's own media type, so the JSON error body
    would be advertised as text/event-stream. FastAPI's built-in 422 applies this
    same no-input test, but documents its own HTTPValidationError shape rather
    than our ValidationProblem, which is why the 422 is ours to prune.
    """
    for operation in iter_operations(schema):
        takes_input = "parameters" in operation or "requestBody" in operation
        if not takes_input:
            operation["responses"].pop("422", None)


def document_errors_as_problem_json(schema: dict[str, Any]) -> None:
    """Move every 4xx/5xx response body to the problem+json media type.

    The handlers answer errors as RFC 9457 problem details, but FastAPI files an
    additional response under the route's own media type (application/json).
    """
    for status_code, response in iter_responses(schema):
        content = response.get("content", {})
        if status_code[0] in "45" and "application/json" in content:
            content[PROBLEM_JSON_MEDIA_TYPE] = content.pop("application/json")


def document_sse_event_names(schema: dict[str, Any]) -> None:
    """Type the SSE stream's `event` field as the `SSEEventName` enum.

    FastAPI's item schema leaves `event` a plain string, and nothing on the
    wire references the enum, so it would never reach the generated client.
    Publishing it as a component lets the frontend check its event map against
    it instead of mirroring the names by hand.
    """
    name = SSEEventName.__name__
    enum_schema = TypeAdapter(SSEEventName).json_schema()
    schema["components"]["schemas"][name] = enum_schema
    responses = schema["paths"][SSE_PATH]["get"]["responses"]
    item_schema = responses["200"]["content"][SSE_MEDIA_TYPE]["itemSchema"]
    item_schema["properties"]["event"] = {"$ref": f"#/components/schemas/{name}"}


class FanfanAPI(FastAPI):
    """FastAPI whose schema goes through the post-processing above.

    Overrides the hook FastAPI's "Extending OpenAPI" guide points at; used at
    every build site so /openapi.json matches the committed spec.
    """

    @override
    def openapi(self) -> dict[str, Any]:
        if self.openapi_schema is not None:
            return self.openapi_schema
        schema = super().openapi()
        drop_unreachable_validation_responses(schema)
        document_errors_as_problem_json(schema)
        document_sse_event_names(schema)
        return schema
