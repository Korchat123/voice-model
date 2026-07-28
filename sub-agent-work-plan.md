# Sub-agent work plan

## Purpose

This document divides the controllable local AI voice project into bounded work
packages that can be delegated safely. The canonical machine-readable task
graph is `sub-agent-tasks.toml`; the product and architecture requirements are
in `voice-model-plan.md`.

Sub-agents must not begin model training, collect voice recordings, select a
model license on the user's behalf, or expose the service outside loopback
without the applicable project decision gate being approved.

## Coordination rules

1. One sub-agent owns each task at a time.
2. Claim a task only when every `depends_on` task is complete.
3. Stay inside the task's declared `write_scope`.
4. Read existing files before editing and preserve unrelated user changes.
5. Do not commit datasets, recordings, generated audio, checkpoints, secrets,
   or experiment outputs.
6. Add or update tests with every production-code change.
7. Record assumptions and unresolved decisions in the task handoff.
8. Do not silently change the public API, dataset schema, or control semantics.
9. Integration happens only after the task's validation and review gates pass.
10. Consent, licensing, security, and release gates cannot be waived by an
    implementation sub-agent.

## Recommended agent roles

### Coordinator

Owns task assignment, decision gates, cross-package integration, and final
acceptance. The coordinator is the only role that should resolve competing
changes to shared root files.

### Foundation agent

Owns repository scaffolding, Python packaging, development tooling, CI, and the
fake-engine development path.

### Governance and documentation agent

Owns consent/provenance templates, voice specification, architecture records,
model-card templates, and ADR preparation. This agent documents choices but
does not provide legal approval.

### Data agent

Owns dataset manifests, validation, splitting, audio-quality checks, and
recording-pipeline tooling. Raw voice data remains outside source control.

### Engine and research agent

Owns baseline comparison, license evidence gathering, engine interfaces, and
engine adapters. Final engine selection remains a coordinator decision gate.

### Training and evaluation agent

Owns reproducible training entry points, checkpoint metadata, control
calibration, offline metrics, and evaluation reports.

### Service agent

Owns the local HTTP API, streaming, cancellation, lifecycle, limits, and
observability. It consumes the engine interface rather than importing a
specific implementation directly.

### Integration agent

Owns the client/provider example, assistant integration guide, contract
fixtures, barge-in behavior, and compatibility tests. Changes to a separate AI
assistant repository require separate authorization.

### Release and security agent

Owns threat modeling, packaging, checksums, SBOM generation, release manifests,
upgrade/rollback procedures, and release readiness checks.

## Execution waves

### Wave 0 — Decisions

Tasks:

- `requirements-and-governance`

Output:

- Confirmed target hardware, languages, voice ownership, consent scope, latency
  targets, and preliminary voice-control definitions.

Gate:

- No dataset collection or engine adaptation until consent and permitted use
  are documented.

### Wave 1 — Parallel foundation work

Tasks:

- `repository-foundation`
- `voice-and-api-specification`
- `baseline-research`

Parallelism:

- These tasks may run concurrently because their write scopes are separate.
- Root configuration files are reserved for `repository-foundation`.
- The coordinator reconciles any proposed dependency or API changes.

Gate:

- Static checks pass, the API contract is reviewed, and viable engine licenses
  are documented.

### Wave 2 — Contracts and data tooling

Tasks:

- `domain-contracts-and-fake-engine`
- `dataset-pipeline`
- `engine-abstraction`

Parallelism:

- Domain contracts must be stable before the service implementation begins.
- Dataset tooling must not depend on the production service.
- Engine adapters must depend only on the engine protocol and domain models.

Gate:

- Fake audio streams through the domain interface.
- Dataset fixtures pass schema, hash, quality, and split-leakage tests.

### Wave 3 — Runtime and evaluation

Tasks:

- `local-synthesis-service`
- `training-and-export`
- `evaluation-harness`

Parallelism:

- The service uses the fake engine until a real adapter is ready.
- Evaluation operates through the engine protocol, allowing fake and real
  implementations.
- Training outputs stay under ignored artifact directories.

Gate:

- Contract, cancellation, dataset, training-smoke, and evaluation-fixture tests
  pass.
- The selected model and its license have coordinator approval.

### Wave 4 — Control calibration and assistant use

Tasks:

- `voice-control-calibration`
- `assistant-integration`

Parallelism:

- Integration may begin with fake-engine presets.
- Real control mappings are accepted only after perceptual evaluation.

Gate:

- Low/neutral/high settings are audibly ordered without unacceptable identity
  or intelligibility regression.
- Barge-in cancels both server synthesis and client playback.

### Wave 5 — Hardening and release

Tasks:

- `security-and-load-hardening`
- `release-packaging`
- `final-acceptance`

Gate:

- Security, load, privacy, license, model-card, rollback, and release-manifest
  checks pass.

## Integration policy

Each sub-agent handoff must include:

- Task ID and completion status.
- Files created or changed.
- Decisions and assumptions.
- Commands run and their results.
- Tests not run and the reason.
- Known risks or follow-up tasks.
- Whether any acceptance criterion remains unmet.

The coordinator should integrate in dependency order, run the full fast test
suite after each wave, and run model-enabled, audio-quality, and load tests at
the relevant gates.

## Definition of done

A task is complete only when:

- All declared deliverables exist.
- Acceptance criteria in `sub-agent-tasks.toml` pass.
- Changes stay within the declared write scope or exceptions are documented.
- Tests and documentation reflect the implementation.
- No private or large generated artifacts are tracked.
- The handoff is complete and the coordinator accepts it.

The project is complete only when the local service can synthesize sanitized
assistant text with versioned voice controls, stream it within the approved
latency budget, cancel it promptly, and pass the consent, quality, security,
integration, and release gates in `voice-model-plan.md`.
