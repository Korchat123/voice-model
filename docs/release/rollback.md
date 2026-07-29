# Upgrade and rollback

- Build once and promote the same verified archive digest.
- Install every release into a new immutable versioned directory.
- Preserve the prior known-good runtime, configuration reference, model digest,
  and compatibility metadata until the observation window closes.
- Stop accepting work, cancel/drain bounded requests, switch the launcher to the
  new version, then verify health, identity, synthesis, cancellation, and logs.
- On any failed check, stop the new process, restore the previous launcher
  target and exact model/config digests, restart, and repeat verification.
- Never roll back to a revoked voice/model or restore deleted private data.
- Record reason, timestamps, artifact hashes, checks, operator, and follow-up.

Rollback is not a substitute for consent revocation. Revoked artifacts must be
disabled even if they were previously known-good.
