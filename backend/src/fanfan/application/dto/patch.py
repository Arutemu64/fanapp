from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema


def _reject_null(value: object) -> object:
    if value is None:
        msg = "cannot be null; omit the field to leave it as is"
        raise ValueError(msg)
    return value


class _NotNull:
    """Marks a PATCH field that may be omitted (left as is) but never sent as null.

    JSON Merge Patch (RFC 7396) reads null as "remove", and none of the fields this
    guards can be cleared, so a null must be a 422 rather than a silent no-op. The
    field keeps its plain ``X | None = None`` shape — a ``SkipJsonSchema[None]``
    union would tag every error path with its branch (``("festival_end",
    "datetime")``), which the SPA's field-error lookup cannot read — and the null
    branch is dropped from the schema here instead, so the spec does not
    advertise null either.
    """

    def __get_pydantic_core_schema__(
        self, source: object, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_before_validator_function(
            _reject_null, handler(source)
        )

    def __get_pydantic_json_schema__(
        self, schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(schema)
        branches = json_schema.get("anyOf")
        if branches is None:
            return json_schema

        non_null = [branch for branch in branches if branch != {"type": "null"}]
        if len(non_null) == 1:
            del json_schema["anyOf"]
            json_schema.update(non_null[0])
        return json_schema


NOT_NULL = _NotNull()
