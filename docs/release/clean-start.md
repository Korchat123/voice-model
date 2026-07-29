# Clean-start verification

1. Use a clean, supported target machine with no existing service, model,
   dataset, environment file, cache, or credentials.
2. Verify the release archive digest out of band, then run
   `python scripts/build_release.py --verify-only --output <archive>`.
3. Inspect the manifest, SBOM, license inventory, compatibility record, and
   model card. Stop if any artifact identity or approval differs.
4. Extract into a new versioned directory as an unprivileged user. Do not reuse
   mutable virtual environments or configuration from another release.
5. Install only from the locked dependency procedure. Keep network binding on
   loopback and create machine-specific configuration outside the release tree.
6. Run health, capabilities, fake synthesis, limits, cancellation, privacy, and
   restart smoke tests.
7. A source/runtime-only archive is not deployable with a voice model until the
   separately approved model digest and compatibility record are verified.

Record the archive hash, target identity, operator, commands, results, and date.
