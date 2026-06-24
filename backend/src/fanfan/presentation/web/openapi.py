from fastapi.routing import APIRoute


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
