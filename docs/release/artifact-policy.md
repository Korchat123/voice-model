# Release artifact policy

The release builder uses an explicit allowlist. It rejects environment files,
keys, certificates, recordings, generated audio, datasets, model/checkpoint
formats, run directories, private paths, caches, symlinks, traversal paths,
duplicate archive members, oversized members, and unresolved approval gates.

The current package is source/runtime-only. Model identity is recorded for
compatibility but weights are never included. A separately controlled model
store must verify the exact approved digest before deployment.

Every archive contains:

- per-file SHA-256 manifest and checksum inventory;
- SPDX-format dependency inventory derived from `uv.lock`;
- project/dependency/model license-review inventory;
- runtime/Python/model compatibility metadata; and
- the explicit unreleased model card and operational procedures.

The generated SBOM records package identity and `NOASSERTION` license values;
human-approved license evidence remains required and must not be inferred from
package metadata.
