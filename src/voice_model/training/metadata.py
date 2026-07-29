"""Canonical JSON metadata helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json(data: dict[str, Any]) -> bytes:
    return (
        json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def write_canonical_json(path: Path, data: dict[str, Any]) -> str:
    payload = canonical_json(data)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()
