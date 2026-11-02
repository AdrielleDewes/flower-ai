"""Explicit annotation preparation or standalone evaluation; never invokes an LLM."""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .annotations import annotation_template, load_annotated_dataset
from .evaluation import evaluate_extractor
from .extractor import QueryExtractor


def main() -> int:
    """Require reviewed annotations and a new output path before evaluating."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--annotation-version", type=int, choices=(1, 2), default=None)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--annotations", type=Path, help="Evaluate using reviewed annotations")
    mode.add_argument("--prepare-annotations", action="store_true", help="Write unreviewed shells only")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; use a new artifact name.")
    try:
        if args.prepare_annotations:
            report = annotation_template(args.dataset, annotation_version=args.annotation_version or 1)
        else:
            prepared = load_annotated_dataset(args.dataset, args.annotations)
            if args.annotation_version is not None and args.annotation_version != prepared.annotation_version:
                raise ValueError("Requested annotation version differs from sidecar version.")
            started = perf_counter()
            extractor = QueryExtractor(prepared.catalog)
            setup_seconds = perf_counter() - started
            report = evaluate_extractor(prepared, extractor)
            report["timing"]["vocabulary_setup_seconds"] = setup_seconds
            report["annotations_sha256"] = hashlib.sha256(args.annotations.read_bytes()).hexdigest()
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(report, output, ensure_ascii=False, indent=2)
            output.write("\n")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Invalid extraction evaluation input/output: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
