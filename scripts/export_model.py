"""Export or verify a deterministic fixture model package."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from voice_model.training.export import export_fixture_model, verify_export


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--run-dir", type=Path)
    result.add_argument("--export-dir", type=Path, required=True)
    result.add_argument("--model-id")
    result.add_argument("--model-version")
    result.add_argument("--verify-only", action="store_true")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.verify_only:
        return 0 if verify_export(args.export_dir) else 1
    if not args.run_dir or not args.model_id or not args.model_version:
        parser().error("--run-dir, --model-id, and --model-version are required for export")
    path = export_fixture_model(
        run_dir=args.run_dir,
        export_dir=args.export_dir,
        model_id=args.model_id,
        model_version=args.model_version,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
