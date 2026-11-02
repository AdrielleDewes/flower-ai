"""Build catalog-specific generation constraints without changing domain schemas."""

from typing import Any

from app.schemas.bouquet_interpretation import BouquetInterpretation
from app.schemas.catalog import InterpretationCatalog

CATALOG_CONSTRAINT_VERSION = 1


def build_catalog_output_schema(catalog: InterpretationCatalog) -> dict[str, Any]:
    """Restrict catalog fields in a fresh inference schema, preserving nulls."""
    schema = BouquetInterpretation.model_json_schema()
    field_options = {
        "occasion": catalog.occasions,
        "styles": catalog.styles,
        "colors": catalog.colors,
        "preferred_flowers": catalog.flowers,
        "excluded_flowers": catalog.flowers,
    }
    for field, options in field_options.items():
        values = list(dict.fromkeys(options))
        property_schema = schema["properties"][field]
        if not values:
            # Empty enums are invalid JSON Schema; an empty category has no selection.
            property_schema.pop("anyOf")
            property_schema["type"] = "null"
            continue
        value_schema = property_schema["anyOf"][0]
        if field == "occasion":
            value_schema["enum"] = values
        else:
            value_schema["items"]["enum"] = values
    return schema
