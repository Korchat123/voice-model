from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from typing import Protocol, cast

import pytest


class ReleaseBuilder(Protocol):
    def build_release(self, config_path: Path, project_root: Path, output: Path) -> str: ...

    def load_config(self, path: Path) -> object: ...

    def verify_release(self, archive_path: Path) -> bool: ...


def load_builder() -> ReleaseBuilder:
    path = Path("scripts/build_release.py")
    spec = importlib.util.spec_from_file_location("release_builder_under_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load release builder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast(ReleaseBuilder, module)


BUILDER = load_builder()


def make_project(root: Path) -> None:
    (root / "src/pkg").mkdir(parents=True)
    (root / "docs/release").mkdir(parents=True)
    (root / "src/pkg/__init__.py").write_text('VERSION = "1"\n', encoding="utf-8")
    (root / "docs/release/README.md").write_text("fixture procedure\n", encoding="utf-8")
    (root / "LICENSE").write_text("Apache-2.0 fixture\n", encoding="utf-8")
    (root / "uv.lock").write_text(
        'version = 1\n[[package]]\nname = "example"\nversion = "1.2.3"\n',
        encoding="utf-8",
    )


def write_config(path: Path, *, approved: bool = True, include_secret: bool = False) -> None:
    includes = ['"LICENSE"', '"uv.lock"', '"src"', '"docs/release"']
    if include_secret:
        includes.append('".env"')
    truth = str(approved).lower()
    model_digest = "a" * 64
    path.write_text(
        f"""
schema_version = 1
release_id = "fixture-1"
runtime_version = "1.0.0"
python_requires = ">=3.11,<3.14"
include = [{", ".join(includes)}]
[model]
id = "approved-model-id"
version = "1.0.0"
sha256 = "{model_digest}"
[approvals]
consent = {truth}
model = {truth}
license = {truth}
provenance = {truth}
security = {truth}
""",
        encoding="utf-8",
    )


def test_release_is_deterministic_and_verifiable(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_project(project)
    config = tmp_path / "release.toml"
    write_config(config)
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    first_hash = BUILDER.build_release(config, project, first)
    second_hash = BUILDER.build_release(config, project, second)
    assert first_hash == second_hash
    assert first.read_bytes() == second.read_bytes()
    assert BUILDER.verify_release(first)
    with zipfile.ZipFile(first) as archive:
        assert ".env" not in archive.namelist()
        assert "RELEASE-MANIFEST.json" in archive.namelist()
        assert "SBOM.spdx.json" in archive.namelist()
        manifest = json.loads(archive.read("RELEASE-MANIFEST.json"))
        assert manifest["model"]["included"] is False


def test_config_fails_closed_on_unapproved_or_placeholder(tmp_path: Path) -> None:
    config = tmp_path / "release.toml"
    write_config(config, approved=False)
    with pytest.raises(ValueError, match="approval consent"):
        BUILDER.load_config(config)
    template = Path("packaging/release.example.toml")
    with pytest.raises(ValueError):
        BUILDER.load_config(template)


def test_forbidden_secret_is_rejected_even_if_allowlisted(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_project(project)
    (project / ".env").write_text("SECRET=do-not-package\n", encoding="utf-8")
    config = tmp_path / "release.toml"
    write_config(config, include_secret=True)
    with pytest.raises(ValueError, match="forbidden"):
        BUILDER.build_release(config, project, tmp_path / "release.zip")


def test_verification_detects_tampering_and_unsafe_members(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_project(project)
    config = tmp_path / "release.toml"
    write_config(config)
    archive = tmp_path / "release.zip"
    BUILDER.build_release(config, project, archive)
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr("../private.env", "SECRET=value")
    assert not BUILDER.verify_release(archive)


def test_missing_required_input_fails(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_project(project)
    config = tmp_path / "release.toml"
    write_config(config)
    (project / "LICENSE").unlink()
    with pytest.raises(FileNotFoundError, match="missing"):
        BUILDER.build_release(config, project, tmp_path / "release.zip")
