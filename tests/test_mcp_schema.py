import pytest
from pydantic import ValidationError, create_model

from src.utils.mcp_client import resolve_type


@pytest.mark.parametrize(
    "values",
    [
        ["read-only", "read_only", "READ_ONLY"],
        ["read only", "read-only"],
        ["*", "value_0"],
        ["_read", "_READ"],
        ["a", "a_2", "A"],
        ["red", "green", "blue"],
        [1, 2, 3],
    ],
)
def test_enum_preserves_every_schema_value(values):
    enum_type = resolve_type({"enum": values}, "choice")
    model = create_model("ToolParameters", choice=(enum_type, ...))

    for value in values:
        parameters = model.model_validate({"choice": value})
        assert parameters.model_dump(mode="json") == {"choice": value}

    assert model.model_json_schema()["$defs"]["choice_Enum"]["enum"] == values


def test_enum_rejects_values_not_in_schema():
    enum_type = resolve_type({"enum": ["read-only", "read_only"]}, "choice")
    model = create_model("ToolParameters", choice=(enum_type, ...))

    with pytest.raises(ValidationError):
        model.model_validate({"choice": "write"})


def test_array_items_keep_all_enum_values():
    values = ["read-only", "read_only"]
    field_type = resolve_type({"type": "array", "items": {"enum": values}}, "choices")
    model = create_model("ToolParameters", choices=(field_type, ...))

    parameters = model.model_validate({"choices": values})
    assert parameters.model_dump(mode="json") == {"choices": values}
