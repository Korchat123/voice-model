"""Build and verify a deterministic, source/runtime-only release archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import tomllib
import zipfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

SCHEMA_VERSION = 1
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
FORBIDDEN_PARTS = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        "data",
        "models",
        "runs",
        "checkpoints",
        "artifacts",
        "exports",
        "private",
        "secrets",
    }
)
FORBIDDEN_ANYWHERE_PARTS = frozenset({".git", ".venv", "__pycache__", "private", "secrets"})
FORBIDDEN_NAMES = frozenset({".env", "id_rsa", "id_ed25519"})
FORBIDDEN_SUFFIXES = frozenset(
    {
        ".wav",
        ".flac",
        ".mp3",
        ".ogg",
        ".m4a",
        ".opus",
        ".pcm",
        ".ckpt",
        ".pt",
        ".pth",
        ".safetensors",
        ".onnx",
        ".bin",
        ".pem",
        ".key",
        ".p12",
        ".pyc",
    }
)
METADATA_NAMES = frozenset(
    {
        "RELEASE-MANIFEST.json",
        "SBOM.spdx.json",
        "LICENSE-INVENTORY.json",
        "COMPATIBILITY.json",
        "CHECKSUMS.sha256",
    }
)


def canonical_json(data: Any) -> bytes:
    return (
        json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class ReleaseConfig:
    release_id: str
    runtime_version: str
    python_requires: str
    include: tuple[str, ...]
    model_id: str
    model_version: str
    model_sha256: str


def _required_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    if "USER_INPUT_REQUIRED" in value:
        raise ValueError(f"{key} contains an unresolved placeholder")
    return value


def load_config(path: Path) -> ReleaseConfig:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    model = data.get("model")
    approvals = data.get("approvals")
    include = data.get("include")
    if not isinstance(model, dict) or not isinstance(approvals, dict):
        raise ValueError("[model] and [approvals] tables are required")
    if (
        not isinstance(include, list)
        or not include
        or not all(isinstance(item, str) and item for item in include)
    ):
        raise ValueError("include must be a non-empty string array")
    for gate in ("consent", "model", "license", "provenance", "security"):
        if approvals.get(gate) is not True:
            raise ValueError(f"approval {gate} must be explicitly true")
    model_sha256 = _required_text(model, "sha256").lower()
    if len(model_sha256) != 64 or any(char not in "0123456789abcdef" for char in model_sha256):
        raise ValueError("model.sha256 must be lowercase SHA-256 hex")
    return ReleaseConfig(
        release_id=_required_text(data, "release_id"),
        runtime_version=_required_text(data, "runtime_version"),
        python_requires=_required_text(data, "python_requires"),
        include=tuple(include),
        model_id=_required_text(model, "id"),
        model_version=_required_text(model, "version"),
        model_sha256=model_sha256,
    )


def _is_forbidden(relative: PurePosixPath) -> bool:
    lowered_parts = tuple(part.casefold() for part in relative.parts)
    name = relative.name.casefold()
    return (
        (bool(lowered_parts) and lowered_parts[0] in FORBIDDEN_PARTS)
        or bool(set(lowered_parts) & FORBIDDEN_ANYWHERE_PARTS)
        or name in FORBIDDEN_NAMES
        or name.startswith(".env.")
        or relative.suffix.casefold() in FORBIDDEN_SUFFIXES
    )


def collect_files(project_root: Path, include: Iterable[str]) -> tuple[tuple[str, Path], ...]:
    root = project_root.resolve()
    collected: dict[str, Path] = {}
    for entry in include:
        pure = PurePosixPath(entry)
        if pure.is_absolute() or ".." in pure.parts or "\\" in entry:
            raise ValueError(f"unsafe include path: {entry}")
        candidate = (root / Path(*pure.parts)).resolve()
        if not candidate.is_relative_to(root):
            raise ValueError(f"include escapes project root: {entry}")
        if not candidate.exists():
            raise FileNotFoundError(f"required release input is missing: {entry}")
        paths = (
            (path for path in candidate.rglob("*") if path.is_file())
            if candidate.is_dir()
            else (candidate,)
        )
        for path in paths:
            relative = PurePosixPath(path.relative_to(root).as_posix())
            if _is_forbidden(relative):
                raise ValueError(f"forbidden release input: {relative}")
            if path.is_symlink():
                raise ValueError(f"symbolic links are not allowed: {relative}")
            collected[str(relative)] = path
    return tuple(sorted(collected.items()))


def dependency_inventory(lock_path: Path) -> tuple[dict[str, str], ...]:
    with lock_path.open("rb") as stream:
        lock = tomllib.load(stream)
    packages = lock.get("package", [])
    if not isinstance(packages, list):
        raise ValueError("uv.lock package inventory is invalid")
    result: list[dict[str, str]] = []
    for package in packages:
        if isinstance(package, dict):
            name = package.get("name")
            version = package.get("version")
            if isinstance(name, str) and isinstance(version, str):
                result.append({"name": name, "version": version})
    return tuple(sorted(result, key=lambda item: (item["name"], item["version"])))


def _metadata(
    config: ReleaseConfig, files: tuple[tuple[str, Path], ...], root: Path
) -> dict[str, bytes]:
    entries = [
        {
            "path": name,
            "sha256": sha256_bytes(path.read_bytes()),
            "size": path.stat().st_size,
        }
        for name, path in files
    ]
    dependencies = dependency_inventory(root / "uv.lock")
    manifest = {
        "schema_version": 1,
        "release_id": config.release_id,
        "runtime_version": config.runtime_version,
        "model": {
            "id": config.model_id,
            "version": config.model_version,
            "sha256": config.model_sha256,
            "included": False,
        },
        "approvals": {
            "consent": True,
            "model": True,
            "license": True,
            "provenance": True,
            "security": True,
        },
        "files": entries,
    }
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": config.release_id,
        "packages": [
            {
                "name": package["name"],
                "versionInfo": package["version"],
                "SPDXID": f"SPDXRef-Package-{index}",
                "downloadLocation": "NOASSERTION",
                "licenseConcluded": "NOASSERTION",
            }
            for index, package in enumerate(dependencies, start=1)
        ],
    }
    licenses = {
        "schema_version": 1,
        "project": {"license": "Apache-2.0", "file": "LICENSE"},
        "dependency_license_review_approved": True,
        "dependencies": dependencies,
        "model_license_review_approved": True,
        "model_artifact_included": False,
    }
    compatibility = {
        "schema_version": 1,
        "release_id": config.release_id,
        "runtime_version": config.runtime_version,
        "python_requires": config.python_requires,
        "model_id": config.model_id,
        "model_version": config.model_version,
        "model_sha256": config.model_sha256,
    }
    metadata = {
        "RELEASE-MANIFEST.json": canonical_json(manifest),
        "SBOM.spdx.json": canonical_json(sbom),
        "LICENSE-INVENTORY.json": canonical_json(licenses),
        "COMPATIBILITY.json": canonical_json(compatibility),
    }
    checksums = "".join(
        f"{sha256_bytes(payload)}  {name}\n" for name, payload in sorted(metadata.items())
    )
    checksums += "".join(f"{sha256_bytes(path.read_bytes())}  {name}\n" for name, path in files)
    metadata["CHECKSUMS.sha256"] = checksums.encode()
    return metadata


def _write_zip_member(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    info.create_system = 3
    archive.writestr(info, payload)


def build_release(config_path: Path, project_root: Path, output: Path) -> str:
    config = load_config(config_path)
    files = collect_files(project_root, config.include)
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    metadata = _metadata(config, files, project_root.resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        for name, path in files:
            _write_zip_member(archive, name, path.read_bytes())
        for name, payload in sorted(metadata.items()):
            _write_zip_member(archive, name, payload)
    if not verify_release(output):
        output.unlink(missing_ok=True)
        raise ValueError("built archive failed self-verification")
    return sha256_bytes(output.read_bytes())


def _safe_archive_name(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or _is_forbidden(path):
        raise ValueError(f"unsafe or forbidden archive member: {name}")
    return path


def verify_release(archive_path: Path) -> bool:
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)) or not set(names) >= METADATA_NAMES:
                return False
            if any(info.is_dir() or info.file_size > 50 * 1024 * 1024 for info in infos):
                return False
            for name in names:
                _safe_archive_name(name)
            checksums = archive.read("CHECKSUMS.sha256").decode("utf-8")
            expected: dict[str, str] = {}
            for line in checksums.splitlines():
                digest, separator, name = line.partition("  ")
                if not separator or len(digest) != 64 or name == "CHECKSUMS.sha256":
                    return False
                expected[name] = digest
            if set(expected) != set(names) - {"CHECKSUMS.sha256"}:
                return False
            if any(sha256_bytes(archive.read(name)) != digest for name, digest in expected.items()):
                return False
            manifest = json.loads(archive.read("RELEASE-MANIFEST.json"))
            licenses = json.loads(archive.read("LICENSE-INVENTORY.json"))
            if not isinstance(manifest, dict) or not isinstance(licenses, dict):
                return False
            model = manifest.get("model")
            if not isinstance(model, dict) or model.get("included") is not False:
                return False
            approvals = manifest.get("approvals")
            if not isinstance(approvals, dict) or any(
                approvals.get(gate) is not True
                for gate in ("consent", "model", "license", "provenance", "security")
            ):
                return False
            model_values = (model.get("id"), model.get("version"), model.get("sha256"))
            if not all(isinstance(value, str) for value in model_values):
                return False
            resolved_model = cast(tuple[str, str, str], model_values)
            model_digest = resolved_model[2]
            if any("USER_INPUT_REQUIRED" in value for value in resolved_model):
                return False
            if len(model_digest) != 64 or any(
                character not in "0123456789abcdef" for character in model_digest
            ):
                return False
            return licenses.get("dependency_license_review_approved") is True
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, json.JSONDecodeError):
        return False


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--config", type=Path)
    result.add_argument("--project-root", type=Path)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--verify-only", action="store_true")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.verify_only:
        return 0 if verify_release(args.output) else 1
    if args.config is None or args.project_root is None:
        parser().error("--config and --project-root are required when building")
    digest = build_release(args.config, args.project_root, args.output)
    print(json.dumps({"archive": str(args.output), "sha256": digest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
