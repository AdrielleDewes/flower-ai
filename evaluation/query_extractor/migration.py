"""Lossless structural migration with explicitly supplied semantic diagnoses."""

from copy import deepcopy
from typing import Any

from .annotation_v2 import FLOWER_FIELDS, UnresolvedReason


def migrate_annotations_v1(
    source: dict[str, Any],
    pending_mentions: dict[tuple[str, str], list[dict[str, Any]]],
) -> dict[str, Any]:
    """Create unapproved v2 annotations, requiring reviewed decisions for pendencies.

    Never infer OUT_OF_CATALOG/UNDECIDED from null or extractor output. The caller
    supplies every old pending field and any new mixed-field mention explicitly.
    Dataset/hash binding and all spans are validated separately by the loader.
    """
    if source.get("annotation_version") != 1:
        raise ValueError("Migration expects annotation_version 1.")
    result = deepcopy(source)
    result["annotation_version"] = 2
    consumed = set()
    for case in result["cases"]:
        case["reviewed"] = False
        for name, old in case["fields"].items():
            if old["state"] not in {"ABSENT", "RESOLVED", "AMBIGUOUS", "CONFLICT"}:
                raise ValueError("Migration requires explicit, valid v1 field states.")
            key = (case["id"], name)
            pending = deepcopy(pending_mentions.get(key, []))
            if key in pending_mentions:
                consumed.add(key)
                if not pending:
                    raise ValueError("An explicit pending decision cannot be empty.")
            if old["state"] in {"AMBIGUOUS", "CONFLICT"} and not pending:
                raise ValueError(f"Explicit pending diagnosis required for {key}.")
            resolved = []
            if old["state"] == "RESOLVED":
                for span in old["evidence"]:
                    item = next((r for r in resolved if r["value"] == span["value"]), None)
                    if item is None:
                        item = {"value": span["value"], "evidence": []}
                        resolved.append(item)
                    item["evidence"].append({k: v for k, v in span.items() if k != "value"})
            if resolved and pending:
                if name not in FLOWER_FIELDS:
                    raise ValueError("Partial migration is supported only for flower fields.")
                state = "PARTIAL"
            elif resolved:
                state = "RESOLVED"
            elif pending:
                conflict = any(
                    p["reason"] == UnresolvedReason.CONFLICTING_INFORMATION.value for p in pending
                )
                state = "CONFLICT" if conflict else "AMBIGUOUS"
            else:
                state = "ABSENT"
            case["fields"][name] = {
                "state": state, "resolved_values": resolved, "unresolved_mentions": pending,
            }
    if consumed != set(pending_mentions):
        raise ValueError("Pending decisions contain unknown case IDs or fields.")
    return result
