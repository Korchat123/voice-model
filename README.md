# Controllable local AI voice

A consent-first, locally deployed text-to-speech project for Thai, English, and
code-switched speech. The planned service streams audio to an AI assistant and
offers bounded controls for prosody and timbre, including a pinched-to-open
resonance control.

The project is in its foundation phase. It does not yet contain a production
voice, trained model, or synthesis endpoint. See
[`voice-model-plan.md`](voice-model-plan.md) for quality gates and
[`sub-agent-work-plan.md`](sub-agent-work-plan.md) for the implementation graph.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) 0.7 or newer
- Python 3.11–3.13 (uv can install an appropriate interpreter)

## Setup

```sh
uv sync --frozen
uv run python -c "import voice_model; print(voice_model.__version__)"
```

Copy `.env.example` to `.env` only when local configuration is needed. Never
commit `.env`, recordings, generated audio, model weights, or training runs.

## Development checks

```sh
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest --cov
make secrets
```

`make check` runs the same quality gate on systems with Make. Expensive model,
training, performance, and release jobs remain explicitly gated until their
phase prerequisites and suitable runners exist.

## Repository boundaries

- `src/voice_model/` contains importable runtime and domain code.
- `tests/` mirrors package boundaries and uses a fake engine in ordinary CI.
- `data/`, `models/`, and `runs/` contain local artifacts; only their guidance
  and approved metadata belong in Git.
- `docs/` records consent, architecture, API, model, and release decisions.
- `configs/` contains reviewed, versioned non-secret configuration.

Use only voices and recordings with documented authorization. Dataset
collection and model training must not begin until consent and provenance gates
are approved.

## License and security

Source code is licensed under Apache-2.0; datasets and model artifacts require
their own explicit license and provenance. Report vulnerabilities according to
[`SECURITY.md`](SECURITY.md).
