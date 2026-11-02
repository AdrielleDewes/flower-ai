"""Catalog generation constraints remain isolated from domain contracts."""

import json

import pytest

from app.schemas.bouquet_interpretation import BouquetInterpretation
from app.schemas.catalog import InterpretationCatalog
from app.services.catalog_output_schema import build_catalog_output_schema


def test_constraints_preserve_domain_contract_and_category_boundaries():
    """Each category restricts its own values without changing domain behavior."""
    catalog = InterpretationCatalog(
        occasions=["Birthday"], styles=["Modern"], colors=["Blue"],
        flowers=["Rose", "Lily"],
    )
    original = BouquetInterpretation.model_json_schema()
    snapshot = catalog.model_dump()
    output = build_catalog_output_schema(catalog)
    options = {
        "occasion": ["Birthday"], "styles": ["Modern"], "colors": ["Blue"],
        "preferred_flowers": ["Rose", "Lily"], "excluded_flowers": ["Rose", "Lily"],
    }
    for field, allowed in options.items():
        prop = output["properties"][field]
        assert prop["anyOf"][1] == {"type": "null"}
        branch = prop["anyOf"][0]
        assert (branch if field == "occasion" else branch["items"])["enum"] == allowed
        assert prop["default"] is None
        assert "minItems" not in branch
        assert "uniqueItems" not in branch
    assert output["properties"]["size"] == original["properties"]["size"]
    assert output["properties"]["budget_max"] == original["properties"]["budget_max"]
    assert output["$defs"] == original["$defs"]
    assert output["additionalProperties"] is False
    assert "required" not in output
    assert BouquetInterpretation.model_json_schema() == original
    assert catalog.model_dump() == snapshot
    assert BouquetInterpretation(colors=[]).colors is None
    assert BouquetInterpretation(colors=["Not in catalog"]).colors == ["Not in catalog"]


@pytest.mark.parametrize("category,field", [
    ("occasions", "occasion"), ("styles", "styles"), ("colors", "colors"),
    ("flowers", "preferred_flowers"), ("flowers", "excluded_flowers"),
])
def test_empty_category_allows_null_without_invalid_empty_enum(category, field):
    """A missing category must never generate an unsatisfiable empty enum."""
    values = {
        "occasions": ["Birthday"], "styles": ["Modern"],
        "colors": ["Blue"], "flowers": ["Rose"],
    }
    values[category] = []
    output = build_catalog_output_schema(InterpretationCatalog(**values))
    assert output["properties"][field]["type"] == "null"
    assert "anyOf" not in output["properties"][field]
    assert '"enum": []' not in json.dumps(output)


def test_catalog_names_round_trip_and_schemas_are_independent():
    """Canonical spelling, special characters, order and tenant isolation survive."""
    names = ["Lírio", "Baby's Breath", 'A "quoted" flower', "Back\\slash", "Lírio"]
    first = InterpretationCatalog(occasions=[], styles=[], colors=[], flowers=names)
    second = InterpretationCatalog(occasions=[], styles=[], colors=[], flowers=["Daisy"])
    output = build_catalog_output_schema(first)
    restored = json.loads(json.dumps(output, ensure_ascii=False))
    enum = restored["properties"]["preferred_flowers"]["anyOf"][0]["items"]["enum"]
    assert enum == names[:-1]
    output["properties"]["preferred_flowers"]["anyOf"][0]["items"]["enum"].append("Other")
    assert first.flowers == names
    assert build_catalog_output_schema(first) == restored
    second_schema = build_catalog_output_schema(second)
    assert second_schema["properties"]["preferred_flowers"]["anyOf"][0]["items"]["enum"] == ["Daisy"]
