# CI/CD and phase-gate contract

> Status: proposed. Repository administrators must configure branch protection,
> environments, runners, and approvals before this contract is enforceable.

## Principles

- GitHub Actions is the orchestration system; workflows use least-privilege
  `GITHUB_TOKEN` permissions and pin third-party actions to reviewed commit SHAs.
- Pull requests run deterministic checks that need no private voice data,
  model weights, GPU, or deployment credentials.
- Model, training, audio, load, and target-hardware jobs run only on labeled,
  access-controlled self-hosted runners after authorization.
- Missing consent, provenance, license review, hardware approval, or required
  evidence blocks promotion. CI never interprets a template as approval.
- Raw/processed recordings, private metadata, generated speech, checkpoints,
  model weights, credentials, and unrestricted logs are never uploaded as
  ordinary GitHub Actions artifacts.
- Every promoted artifact is immutable, checksummed, traceable to a commit,
  configuration, dependency lock, dataset manifest, model, and workflow run.

## Workflow events and job classes

| Event | Purpose | Allowed job class |
|---|---|---|
| `pull_request` | Fast validation and review evidence | Fast only |
| Push to protected `main` | Re-run fast suite; build non-sensitive candidates | Fast |
| `workflow_dispatch` | Approved model, benchmark, training, load, or promotion run | Model-enabled after environment approval |
| Version tag such as `v*` | Reproducible release candidate and attestations | Fast plus approved release jobs |
| Scheduled | Dependency/security scan and optional runner health check | Fast; model runner only if separately approved |

Do not use `pull_request_target` to execute pull-request code. Fork pull
requests receive no secrets and cannot use self-hosted model runners.

### Fast jobs

Run on ephemeral GitHub-hosted runners with locked dependencies and no project
secrets:

- repository policy, Markdown, TOML/YAML/schema, and provenance-reference checks;
- secret scanning, dependency review, license policy, and static security checks;
- formatting, linting, type checking, unit tests, fake-engine contract tests;
- deterministic dataset-manifest tests using small licensed synthetic fixtures;
- package metadata, release-layout, and documentation link checks.

Fast jobs must not download restricted models or access voice datasets.

### Model-enabled jobs

Run on dedicated self-hosted labels such as
`[self-hosted, voice-model, approved]`; add `gpu` or the exact target-hardware
label only when required. Use a protected GitHub Environment with named
reviewers, concurrency limits, job timeouts, and cleanup in an `always()` step.

This class includes real-engine integration, baseline benchmarks, training
smoke/full training, perceptual sample generation, audio evaluation, target
hardware performance, load tests, packaging with weights, and deployment
verification. Results uploaded to GitHub must be sanitized summaries; private
artifacts go to the approved restricted artifact store.

## Required checks and task mapping

Check names should remain stable because branch protection refers to them.
“Evidence” means a sanitized, machine-readable report plus hashes/references to
restricted evidence where necessary.

| Wave / task | Trigger and jobs | Required checks | Evidence/artifacts | Promotion gate |
|---|---|---|---|---|
| Wave 0 — `requirements-and-governance` | PR fast docs/schema validation; manual governance review outside CI | `docs`, `governance-template-safety`, `provenance-schema` | Non-sensitive checklist and reviewed document hashes | Signed consent and approvals must be verified by authorized reviewers; templates and `USER_INPUT_REQUIRED` values never pass the gate |
| Wave 1 — `repository-foundation` | Every PR and `main` push, fast | `lint`, `format`, `typecheck`, `unit`, `secret-scan`, `dependency-review` | Test and scan summaries | All protected checks pass from a clean locked install |
| Wave 1 — `voice-and-api-specification` | Relevant PRs, fast contract/schema tests | `api-contract`, `docs`, `config-schema` | OpenAPI/config diff and contract report | Reviewed versioning, limits, cancellation, errors, loopback default, and no-path contract |
| Wave 1 — `baseline-research` | PR fast evidence validation; manual target-run model job | `baseline-evidence`, `license-review`; `baseline-target-benchmark` after approval | License/source matrix; sanitized benchmark JSON; private audio remains restricted | Governance complete, licenses reviewed, one candidate passes approved hardware budget |
| Wave 2 — `domain-contracts-and-fake-engine` | Every relevant PR, fast | `unit-domain`, `unit-engines`, `fake-contract` | Test report and deterministic fixture hashes | Bounds, deterministic chunks, and cancellation contract pass |
| Wave 2 — `dataset-pipeline` | PR fast fixture tests; manual restricted-data validation | `unit-data`, `dataset-fixture`; `dataset-acceptance` on approved runner | Schema/leakage/QC summary and manifest hash; no recordings | Consent scope verified, required metadata present, and split leakage is zero |
| Wave 2 — `engine-abstraction` | PR fast adapter unit tests; manual model integration | `unit-engine-adapters`; `real-engine-integration` | Capability/version report; sanitized load/cleanup metrics | License-approved engine implements only shared contract and reports unsupported controls |
| Wave 3 — `local-synthesis-service` | PR fast fake-engine contract/integration; manual bounded load smoke | `service-contract`, `service-integration`, `service-security-smoke` | JUnit/coverage and privacy-safe diagnostics | Loopback, limits, backpressure, idempotent cancellation, and cleanup pass |
| Wave 3 — `training-and-export` | PR fast config/unit tests; manual model runner | `unit-training`; `training-smoke`, then separately approved `training-full` | Reproducibility metadata and hashes in restricted store; sanitized metrics | Governance/data/engine gates pass; smoke is reproducible; full training requires explicit environment approval |
| Wave 3 — `evaluation-harness` | PR fast metric fixture tests; manual model/audio run | `unit-evaluation`, `audio-fixture`; `model-evaluation` | Sanitized per-language metric report; blinded audio remains restricted | Thai, English, mixed, controls, identity, quality, and performance are reported separately as specified |
| Wave 4 — `voice-control-calibration` | PR fast mapping tests; manual model generation/listening | `unit-controls`; `control-evaluation`, `listening-approval` | Versioned mapping/preset hashes and sanitized blinded-study summary | Low/neutral/high are monotonic; boundaries/combinations pass; identity and intelligibility stay within approved limits |
| Wave 4 — `assistant-integration` | PR fast fake-service integration; approved local end-to-end run | `assistant-integration`; `assistant-e2e` | Cancellation/fallback diagnostic report without speech text | Sanitized text only; barge-in, reconnect, mute, fallback, and failure isolation pass |
| Wave 5 — `security-and-load-hardening` | PR fast security tests; manual approved load runner | `security`, `privacy-log`; `load`, `cancellation-race` | Sanitized findings, resource curves, and remediation references | No high/critical unresolved issue; logs contain no text/secrets; memory and rejection remain bounded |
| Wave 5 — `release-packaging` | Tag or manual release-candidate workflow | `release-layout`, `sbom`, `license-bundle`, `artifact-scan`, `reproducibility` | Checksums, SBOM, notices, model card, compatibility manifest, provenance attestation | All dependencies pass; package contains no recordings/secrets/private metadata; protected release approval granted |
| Wave 5 — `final-acceptance` | Manual workflow on exact release commit/artifacts | Every required fast and approved model check plus `final-traceability` | Signed-off traceability index linking immutable evidence | Quality, hardware, consent, provenance, license, privacy, rollback, and integration approvals are complete |

The project’s numbered implementation phases map to these checks by ownership:
Phase 0 uses Wave 0; Phase 1 uses repository/API/domain/service fake checks;
Phase 2 uses baseline checks; Phase 3 uses dataset checks; Phases 4–5 use
training, control, and evaluation checks; Phase 6 uses service/security/load;
Phase 7 uses assistant checks; Phase 8 uses release/final-acceptance checks.

## Workflow structure

Recommended workflow files:

- `ci.yml`: PR and `main` fast matrix with dependency caching keyed by lockfile.
- `security.yml`: scheduled and PR secret/dependency/static security checks.
- `model-validation.yml`: manual, protected model/target-hardware jobs.
- `release.yml`: tag/manual build, attest, promote, deploy, and verify jobs.

Use path filters only to avoid irrelevant expensive jobs; never path-filter
away policy, secret, or release-integrity checks. Use reusable workflows with
explicit typed inputs. Set explicit `permissions`, `timeout-minutes`, and
`concurrency` on every workflow. Cancel superseded PR runs, but never cancel an
in-progress release promotion without an auditable operator decision.

## Artifacts and retention

Public/ordinary Actions artifacts may contain:

- JUnit, coverage, lint, schema, SBOM, license, and sanitized benchmark reports;
- hashes and opaque IDs for restricted datasets/models;
- small synthetic or explicitly redistributable fixtures.

They must not contain:

- voice recordings or generated samples tied to a private voice;
- transcripts or prompts classified as private/held-out;
- datasets, checkpoints, weights, identity/contact/signature data;
- absolute private paths, environment dumps, tokens, or unredacted logs.

Set the shortest practical GitHub retention. Restricted artifacts use encrypted
approved storage with access logs, retention/deletion rules, immutable version
IDs, and SHA-256 verification. Promotion copies by digest, never by mutable
filename such as `latest`.

## Secrets, privacy, and runner controls

- Store deployment credentials only in protected GitHub Environments or an
  approved short-lived identity provider; prefer OIDC over long-lived secrets.
- Scope environment secrets to the exact promotion job. Build/test jobs receive
  no production credentials.
- Masking is not a substitute for avoiding sensitive output. Never echo
  contexts, command environments, synthesis text, signed consent, or manifests
  containing personal data.
- Protect self-hosted runners from untrusted code, isolate each job, restrict
  egress, mount private data read-only where possible, and securely clean work,
  caches, temporary audio, and accelerator memory after every run.
- Do not cache model data or private manifests through GitHub-hosted cache.
- Scan release contents and logs for secrets, recordings, private metadata, and
  forbidden file types before signing.
- Environment approvals must be performed by someone other than the actor who
  initiated promotion when repository staffing permits.

## Release promotion and local deployment

Use protected environments in order:

1. `model-validation`: verify exact model/config/dataset digests on approved
   hardware.
2. `release-candidate`: build once from a protected tag/commit, produce SBOM,
   notices, compatibility metadata, checksums, provenance attestation, and
   signatures.
3. `local-staging`: deploy that same digest to an isolated local target, then
   run health, capabilities, synthesis, cancellation, restart, upgrade,
   clean-start, and rollback smoke tests.
4. `local-production`: after final approval, promote the already-tested digest;
   do not rebuild. Verify health and version, retain the prior known-good digest,
   and automatically roll back on failed post-deployment checks.

A GitHub Release may publish only artifacts whose distribution is explicitly
permitted. Private/local-only weights remain in the restricted store; the
GitHub Release can contain checksums and approved metadata without the weights.
Deployment should default to manual dispatch because the service and model are
local and hardware-specific.

## Branch protection and exceptions

Protect `main`; require pull requests, current required checks, resolved review
threads, and at least one independent approval. Prevent force pushes and branch
deletion. Require signed commits/tags when repository policy supports them.

An emergency exception must record approver, reason, scope, exact commit and
artifact digest, time limit, checks skipped, compensating controls, and a
follow-up issue. It cannot waive consent, provenance, permitted-use, secret
exposure, or artifact-integrity requirements.
