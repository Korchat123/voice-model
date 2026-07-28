# Contributing

## Before starting

Read the project plan, relevant architecture decisions, and consent policy.
Never introduce recordings, model weights, generated audio, private metadata,
credentials, or machine-specific paths into Git.

## Workflow

1. Create a focused branch and keep changes within one task's declared scope.
2. Add or update tests for behavior changes.
3. Run `uv sync --frozen` and `make check`.
4. Use a concise conventional commit such as `feat(service): add cancellation`.
5. Describe security, privacy, licensing, and compatibility effects in review.

Do not silently weaken quality thresholds. A deferred model-dependent check
must be visibly gated and documented, not replaced by a passing placeholder.

## Code standards

- Support Python 3.11–3.13 and keep production code under `src/voice_model`.
- Add type annotations and satisfy strict mypy.
- Use Ruff for linting and formatting.
- Keep unit tests deterministic and independent of large model artifacts.
- Keep scripts thin; reusable behavior belongs in the package.

By contributing, you certify that you have the right to submit the work under
this repository's license. This does not grant permission to contribute voice
recordings or model artifacts.

