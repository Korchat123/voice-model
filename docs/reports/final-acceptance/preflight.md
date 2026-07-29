# Final acceptance preflight

- Audit date: 2026-07-29
- Audited revision: `7872bf7`
- Workflow recheck: current working tree after protected-command corrections
- Sources: `voice-model-plan.md` and `sub-agent-tasks.toml`
- Outcome: **NOT READY FOR FINAL ACCEPTANCE**

This is a preflight traceability audit, not final acceptance, release approval,
model approval, legal review, or permission to collect voice data or train.
Passing fixture tests proves that infrastructure behaves as tested; it does
not prove that a real voice/model is accurate, natural, licensed, consented,
fast enough, or safe to release.

## Automated evidence observed

These commands were run from the repository root using the existing virtual
environment:

```powershell
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\mypy.exe
.\.venv\Scripts\pytest.exe -q
.\.venv\Scripts\pytest.exe --cov -q
.\.venv\Scripts\python.exe scripts\prepare_dataset.py --help
.\.venv\Scripts\python.exe scripts\evaluate.py --help
.\.venv\Scripts\python.exe scripts\train.py --help
.\.venv\Scripts\python.exe scripts\export_model.py --help
.\.venv\Scripts\pytest.exe -q tests\release
.\.venv\Scripts\python.exe scripts\build_release.py --verify-only --output runs\release-preflight
```

Observed results:

- formatting: 100 files already formatted;
- lint: passed;
- strict typing: 58 source files passed;
- tests: 118 passed;
- coverage gate: 118 passed, 83.01% total coverage against the 80% minimum;
- fast phase subsets: contracts/data 59 passed; service 17 passed;
  training/evaluation 16 passed; controls/assistant 14 passed; security 12
  passed;
- release tests: 5 passed;
- all four CLI help/smoke commands exited successfully.
- release verification returned exit code 1, as expected, because no approved
  release archive exists at `runs/release-preflight`.

These results cover only checked-in code and synthetic/deterministic fixtures.
No model was downloaded, no private dataset was inspected, no real voice was
generated, no target-hardware benchmark ran, and no listener study occurred.

## Task and gate traceability

Status meanings:

- **Infrastructure complete**: implementation/docs and fixture tests exist.
- **Partial**: infrastructure exists but a required real-world acceptance item
  is absent.
- **Blocked**: prerequisite approval or evidence is explicitly unset.
- **Missing**: required implementation/deliverable is absent.

| Task | Preflight status | Implemented evidence | Unmet acceptance gate |
|---|---|---|---|
| `requirements-and-governance` | **Blocked** | Consent, provenance, revocation, voice-specification, target-hardware, held-out-set, and model-card templates exist | Consent is unsigned; voice identity/use/accent/review fields remain `USER_INPUT_REQUIRED`; hardware and evaluation owners/threshold approvals are unset |
| `repository-foundation` | **Infrastructure complete** | Python src layout, locked dependencies, ignore policy, docs, expanded fast/protected/release CI workflows, lint/type/test configuration | Fresh-checkout hosted CI results and repository branch/environment protection were not independently verified by this local preflight |
| `voice-and-api-specification` | **Infrastructure complete; manual review pending** | Versioned API, streaming framing, cancellation, limits, errors, preset schemas, architecture ADR | Required human API/governance review is not recorded |
| `baseline-research` | **Blocked** | Current official-source comparison, license questions, benchmark protocol, provisional MOSS-first recommendation | `configs/evaluation/baselines.toml` is `unmeasured`; immutable model revisions, exact artifact/license approval, target-hardware results, and accepted baseline are absent |
| `domain-contracts-and-fake-engine` | **Infrastructure complete** | Typed domain contracts, deterministic bounded fake PCM engine, cancellation token, unit tests | This proves only the fake boundary, not a selected model |
| `dataset-pipeline` | **Infrastructure complete; real data blocked** | Manifest/schema, hash/QC/duplicate/leakage/split logic and fixture tests | Consent is not signed; recording collection is unauthorized; approved real manifest and dataset acceptance report do not exist |
| `engine-abstraction` | **Partial** | Approval-gated registry, capability filtering, model identity checks, deterministic test adapter | No approved selected-engine adapter, model loading/cleanup integration tests, or `tests/integration/engines/` evidence exists |
| `local-synthesis-service` | **Infrastructure complete for fake engine** | Loopback defaults, health/capabilities/synthesis/cancel routes, limits, queue/backpressure, contract and lifecycle tests | Real-engine streaming, real compute cancellation, memory/VRAM cleanup, and target-runtime behavior are unmeasured |
| `training-and-export` | **Infrastructure complete for fixture only; blocked for real training** | Reproducible fixture config/run/checkpoint/export metadata and smoke tests | Code intentionally exports fixture-only runs; consent, approved dataset/engine, real training, held-out checkpoint selection, and reproducibility evidence are absent |
| `evaluation-harness` | **Infrastructure complete; real evaluation blocked** | PCM quality, intelligibility proxy, edit-rate math, latency/RTF/cancel/control structures, report format, listening protocol | ASR/speaker adapters are deliberately unset; no Thai/English/mixed model results, identity scores, performance run, combinations, or listening results exist |
| `voice-control-calibration` | **Blocked** | Versioned bounded interpolation, capability filters, safe-neutral logic, resonance ordering, tests, report template | Mapping config is unmeasured/unapproved; thresholds are unset; no blinded low/neutral/high or combination study; no identity-drift evidence; presets are not perceptually approved |
| `assistant-integration` | **Infrastructure complete against fake service** | Reference provider, sanitized speech boundary, streaming/cancel/fallback behavior, integration tests | No approved real-engine end-to-end playback, reconnect, mute, lip-sync/timing, or target-assistant acceptance report exists |
| `security-and-load-hardening` | **Partial** | Threat model, malformed-input/privacy/log-leakage tests, bounded fake-engine load tests, initial report | Report explicitly excludes penetration testing, RSS/VRAM measurement, real cancellation races, authentication/TLS/browser-origin/OS sandboxing, and multi-process deployment |
| `release-packaging` | **Infrastructure complete; real release blocked** | Deterministic source/runtime archive builder, forbidden-artifact scan, manifest, SBOM, license inventory, compatibility metadata, checksums, model-card status, rollback/clean-start/deletion guidance, protected workflow, and five release tests | Example config deliberately contains unresolved approvals/model digest; no approved model, complete model card, restricted-store archive, signature/attestation, deployment, rollback execution, or release approval exists |
| `final-acceptance` | **Blocked** | This preflight report only | Dependencies are incomplete; no signed quality/performance/security/license/integration/governance sign-off or exact release artifact exists |

## Wave gates

| Wave | Gate result | Reason |
|---|---|---|
| Wave 0 — Decisions | **Fail / blocked** | Templates are present, but consent, permitted use, voice specification, target hardware, held-out set, and measurable targets are not approved |
| Wave 1 — Foundation | **Partial** | Static infrastructure and API/baseline documents exist; API/license reviews and measured baseline approval do not |
| Wave 2 — Contracts and data | **Partial** | Fake-engine and dataset-fixture tests pass; real dataset acceptance and selected adapter integration do not |
| Wave 3 — Runtime and evaluation | **Partial** | Fake-service, fixture-training, and metric infrastructure pass; real model, dataset, hardware, and quality evidence do not |
| Wave 4 — Controls and integration | **Partial** | Fake integration and mapping mechanics pass; controls/listening and real assistant end-to-end acceptance do not |
| Wave 5 — Hardening and release | **Fail / blocked** | Packaging and CI scaffolding now exist, but hardening is fake-engine/initial only and no approved, built, deployed, rollback-tested release artifact exists |

## Project-plan phase assessment

- Phase 0 is blocked by unsigned consent and unapproved requirements.
- Phase 1 has substantial deterministic infrastructure, but its manual contract
  and fresh-checkout/branch-protection evidence is incomplete.
- Phase 2 has research only; no target-hardware baseline measurement or approved
  engine selection exists.
- Phase 3 has dataset tooling only; collection must not begin before consent.
- Phase 4 has fixture training and calibration mechanics only; no real
  adaptation or approved controls exist.
- Phase 5 has evaluation/security scaffolding only; no real-model or listening
  results exist.
- Phase 6 has a fake-engine local service only.
- Phase 7 has a fake-service reference assistant integration only.
- Phase 8 has packaging and operational-document infrastructure, but no approved
  model release, restricted-store artifact, deployment, rollback execution, or
  maintenance evidence.

The first milestone in `voice-model-plan.md` is therefore incomplete. In
particular, requirements/hardware, signed consent, accepted baseline benchmark,
and approved voice specification remain outstanding.

## Defects and discrepancies

1. **No real release artifact:** packaging mechanics and tests exist, but the
   example config deliberately fails closed on consent/model/license/provenance/
   security approvals. `--verify-only` correctly returns failure when pointed
   at a nonexistent preflight archive.
2. **Selected adapter deliverable absent:** the registry is intentionally
   generic and approval-gated. This is correct safety behavior, but it does not
   satisfy the task's selected real-engine adapter/loading/cleanup deliverable.
3. **Real evaluation cannot run as specified:** approved ASR and speaker-metric
   adapter revisions remain `UNSET`; no real per-language report exists.
4. **Control task is mechanics, not calibration:** configs explicitly state
   `unmeasured`, mappings are not approved, and perceptual thresholds are unset.
5. **Hardening scope is narrower than acceptance:** the initial report uses the
   deterministic fake engine and does not demonstrate real memory/VRAM bounds,
   real cancellation behavior, or deployment security.
6. **CI/CD administration is not locally verifiable:** workflow files now cover
   fast, protected-model/hardware, and protected-release classes, but branch
   protection, environments, runners, and approvals still require repository
   administrator configuration. Local tests cannot verify those controls.
7. **Commit wording overstates calibration:** commit `8f23d4d` is titled
   “Add measured voice controls…” while checked-in calibration evidence is
   explicitly unmeasured/unapproved. The code is fail-closed, but the history
   label should not be treated as evidence.

### Resolved workflow findings

The earlier protected-workflow command mismatch is resolved in the current
working tree:

- model evaluation supplies every argument required by `scripts/evaluate.py`
  from protected variables and validates the language enum;
- control/listening validation no longer calls nonexistent CLI flags and
  verifies a non-empty restricted evidence file against its immutable SHA-256;
- release construction now passes `--project-root .`; verification points to
  the same configured output archive.

This confirms command/configuration alignment only. The protected jobs were not
executed because approved runners, artifacts, evidence, and environment
approvals are not available in this preflight.

The earlier preflight's encoding-corruption finding was false. UTF-8-aware
inspection shows correct Unicode em dashes, smart quotes, arrows, box-drawing
characters, and ≤ symbols; the mojibake came from PowerShell display decoding.

## Exact remaining validation commands

The following are required after their prerequisites and paths exist. They are
listed for traceability and were **not** run where inputs/implementations are
missing:

```powershell
# Governance: manual, authorized review; no command can sign consent.
rg -n "USER_INPUT_REQUIRED|UNSET_" docs configs

# Locked clean-install validation.
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest -q

# Current deterministic boundaries.
uv run pytest -q tests/unit/domain tests/unit/engines
uv run pytest -q tests/unit/data
uv run pytest -q tests/contract tests/integration/service
uv run pytest -q tests/unit/training tests/integration/training
uv run pytest -q tests/unit/evaluation tests/audio_quality
uv run pytest -q tests/unit/inference
uv run pytest -q tests/integration/assistant
uv run pytest -q tests/security
uv run pytest -q -m load tests/load

# After an approved model adapter is implemented and artifacts are provisioned.
uv run pytest -q -m model tests/integration/engines

# Current release infrastructure. Verification must point to an existing archive.
uv run pytest -q tests/release
uv run python scripts/build_release.py --verify-only --output <existing-release.zip>

# After all approvals are resolved, build once and verify the same archive.
uv run python scripts/build_release.py --config <approved-release.toml> --project-root . --output <release.zip>
uv run python scripts/build_release.py --verify-only --output <release.zip>
```

In addition, protected/manual jobs must run the baseline protocol, real dataset
acceptance, model training/evaluation, blinded listening study, target-hardware
latency/RTF/cancellation/load tests, assistant end-to-end tests, package scan,
SBOM/license/checksum generation, rollback/restore, and governance review.
Those jobs must reference immutable model, dataset, config, code, and artifact
revisions.

## Minimum path to a future final-acceptance run

1. Complete and sign consent outside the public repository; approve voice
   specification, use scope, held-out set, target hardware, and thresholds.
2. Pin and legally review exact baseline artifacts; benchmark them on the exact
   target and approve one candidate.
3. Collect only authorized data, pass the real dataset gate, implement the
   selected adapter, and verify model load/cleanup/cancellation.
4. Run approved training only after preceding gates; produce reproducible
   checkpoint and provenance records.
5. Produce real Thai, English, mixed, control, identity, latency, audio, and
   blinded-listening results; approve only passing controls.
6. Complete real-engine security/load and assistant end-to-end acceptance.
7. Implement release packaging, SBOM/licenses/checksums/model card,
   compatibility, rollback, deletion, and revocation procedures.
8. Run final validation on the exact immutable release commit and artifact,
   then obtain independent authorized sign-offs.

Until all eight steps have evidence, this repository must remain pre-release
infrastructure and must not be represented as an accepted AI voice model.
