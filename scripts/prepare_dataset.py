"""Validate and deterministically split a dataset manifest."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from voice_model.data.manifest import load_manifest, write_manifest
from voice_model.data.splits import assign_splits
from voice_model.data.validation import validate_manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("manifest", type=Path, help="Input JSON manifest")
    result.add_argument(
        "--dataset-root", type=Path, required=True, help="Root for relative audio paths"
    )
    result.add_argument("--output", type=Path, help="Write split manifest to this path")
    result.add_argument("--seed", help="Stable split seed; required with --output")
    result.add_argument("--train-ratio", type=float, default=0.8)
    result.add_argument("--validation-ratio", type=float, default=0.1)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    manifest = load_manifest(args.manifest)
    if args.output:
        if not args.seed:
            parser().error("--seed is required with --output")
        manifest = assign_splits(
            manifest,
            seed=args.seed,
            train_ratio=args.train_ratio,
            validation_ratio=args.validation_ratio,
        )
    findings = validate_manifest(manifest, args.dataset_root)
    print(
        json.dumps(
            {
                "schema_version": manifest.schema_version,
                "dataset_id": manifest.dataset_id,
                "dataset_version": manifest.dataset_version,
                "valid": not findings,
                "findings": [
                    {"code": item.code, "clip_id": item.clip_id, "message": item.message}
                    for item in findings
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if findings:
        return 1
    if args.output:
        write_manifest(manifest, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
