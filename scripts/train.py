"""Run deterministic fixture training infrastructure."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from voice_model.training.config import load_training_config
from voice_model.training.run import run_fixture_training


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("config", type=Path)
    result.add_argument("--dataset-root", type=Path, required=True)
    result.add_argument("--output-dir", type=Path, required=True)
    result.add_argument("--code-revision", required=True)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    result = run_fixture_training(
        load_training_config(args.config),
        dataset_root=args.dataset_root,
        output_dir=args.output_dir,
        code_revision=args.code_revision,
    )
    print(
        json.dumps(
            {
                "fixture_only": True,
                "run_metadata": str(result.run_metadata_path),
                "run_metadata_sha256": result.run_metadata_sha256,
                "selected_checkpoint": result.selected_checkpoint.to_dict(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
