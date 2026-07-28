# Controllable local AI voice — project plan

## 1. Goal

Build a consented, distinctive text-to-speech (TTS) voice that:

- Runs locally on the selected target hardware.
- Can be used by an AI assistant through a provider-neutral API.
- Supports predictable voice controls such as pitch, pace, energy, warmth,
  breathiness, brightness, and pinched/nasal resonance.
- Streams audio with low first-audio latency and supports cancellation.
- Is reproducible, testable, versioned, and safe to distribute.

Speech recognition and agent reasoning are outside this repository. The AI
application decides what text is safe to speak; this service only synthesizes
the bounded text it receives.

## 2. Product boundaries

This repository owns:

- Voice consent, provenance, and permitted-use records.
- Recording scripts, source-audio manifests, and dataset tooling.
- Audio validation, cleaning, segmentation, transcripts, and pronunciation.
- Baseline evaluation, training/adaptation, and checkpoint selection.
- Voice-control calibration and evaluation.
- Model export and the local streaming synthesis service.
- Optional phoneme and viseme timing for avatar lip synchronization.

The AI application owns:

- Conversation state and agent/tool execution.
- Selection and sanitization of text allowed to be spoken.
- Provider selection, playback, mute, and interruption state.
- UI, transcript display, and avatar rendering.

The voice service must never receive tool credentials, conversation databases,
arbitrary filesystem paths, or raw private history.

## 3. Decisions required before implementation

Record these decisions in `docs/decisions/`:

- [ ] Voice owner identity and written consent.
- [ ] Original voice, adapted voice, or a licensed synthetic base.
- [ ] Supported languages, accents, and code-switching requirements.
- [ ] Permitted use, retention, redistribution, and revocation terms.
- [ ] Target operating system, CPU/GPU, RAM/VRAM, and storage.
- [ ] Maximum first-audio latency and acceptable real-time factor.
- [ ] Required output format and avatar timing requirements.
- [ ] Whether generated-audio disclosure or watermarking is required.

Initial working assumptions, to be confirmed:

- Primary deployment: one local AI assistant and one concurrent stream.
- Languages: Thai and English, including code-switching.
- Output: 24 kHz mono PCM streaming, with WAV available for debugging.
- Voice controls are optional and default to the calibrated neutral voice.

Do not collect or train on third-party voices without explicit authorization.
Do not use scraped celebrity, actor, streamer, or private recordings.

## 4. Voice-control design

### 4.1 Public controls

Expose normalized controls with a safe range of `-1.0` to `1.0`. Zero means the
calibrated base voice:

- `pitch`: perceived fundamental frequency.
- `pace`: speaking rate without changing pitch.
- `energy`: vocal intensity.
- `warmth`: darker/softer versus cooler tone.
- `brightness`: spectral brightness.
- `breathiness`: airy versus pressed phonation.
- `resonance`: fuller/open versus pinched/nasal resonance.
- `expressiveness`: variation in pitch, rhythm, and emphasis.
- `style`: named preset such as `neutral`, `warm`, `cheerful`, `serious`, or
  `thinking`.

Use `resonance < 0` for a more pinched/nasal quality and `resonance > 0` for a
more open/full quality. UI labels may say “pinched ↔ open,” while the API keeps
the acoustically clearer `resonance` name.

### 4.2 Control implementation

Use this priority order:

1. Model-native conditioning or style embeddings for natural timbre changes.
2. Prosody conditioning for pitch, duration, energy, and expressiveness.
3. Pronunciation and text normalization before synthesis.
4. Bounded DSP only for small final adjustments and output normalization.

Do not market a control as supported until it passes listening tests for:

- Audible effect across its range.
- Minimal identity drift.
- Minimal intelligibility loss.
- Monotonic behavior between low, neutral, and high settings.
- No clipping, metallic artifacts, or unstable loudness.

Create named presets from versioned control values. Do not hide untracked
model prompts or magic constants in application code.

## 5. Service contract

Use a versioned HTTP API initially. Design the domain layer so transport can be
replaced by WebSocket or gRPC without changing synthesis logic.

```ts
type VoiceControls = {
  pitch?: number;
  pace?: number;
  energy?: number;
  warmth?: number;
  brightness?: number;
  breathiness?: number;
  resonance?: number;
  expressiveness?: number;
};

type SynthesisRequest = {
  requestId: string;
  text: string;
  language: "th" | "en" | "auto";
  voice: string;
  style?: "neutral" | "warm" | "cheerful" | "serious" | "thinking";
  controls?: VoiceControls;
  seed?: number;
  returnTimings?: boolean;
};

type SynthesisMetadata = {
  requestId: string;
  modelId: string;
  modelVersion: string;
  runtimeVersion: string;
  sampleRate: number;
  encoding: "pcm_s16le" | "wav";
  durationMs?: number;
  appliedControls: Required<VoiceControls>;
  phonemes?: Array<{ symbol: string; startMs: number; endMs: number }>;
  visemes?: Array<{ id: string; startMs: number; endMs: number }>;
};
```

Required endpoints:

- `GET /v1/health`: liveness and readiness without loading private data.
- `GET /v1/capabilities`: voices, languages, controls, limits, and versions.
- `POST /v1/synthesis`: bounded streaming synthesis response.
- `DELETE /v1/synthesis/{requestId}`: idempotent cancellation.

Required behavior:

- Validate all fields and reject unknown or out-of-range controls.
- Enforce text, request-time, output-duration, and concurrency limits.
- Return machine-readable errors and model/version headers.
- Never accept input or output file paths.
- Stop model work and release buffers promptly after cancellation.
- Avoid logging full synthesis text by default.
- Bind to loopback by default; require explicit configuration for remote access.

## 6. Repository structure

Use a Python `src` layout for the model and service, with tooling separated from
runtime code:

```text
voice-model/
├── README.md
├── LICENSE
├── SECURITY.md
├── CONTRIBUTING.md
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env.example
├── Makefile
├── configs/
│   ├── data/
│   ├── training/
│   ├── inference/
│   └── evaluation/
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── voice-specification.md
│   ├── consent/
│   │   ├── consent-template.md
│   │   ├── provenance-template.yaml
│   │   └── revocation-process.md
│   ├── decisions/
│   │   ├── 0001-tts-baseline.md
│   │   └── 0002-audio-api.md
│   └── model-card-template.md
├── src/
│   └── voice_model/
│       ├── __init__.py
│       ├── domain/
│       │   ├── controls.py
│       │   ├── requests.py
│       │   └── errors.py
│       ├── data/
│       │   ├── manifest.py
│       │   ├── validation.py
│       │   ├── segmentation.py
│       │   └── normalization.py
│       ├── engines/
│       │   ├── base.py
│       │   └── adapters/
│       ├── training/
│       │   ├── train.py
│       │   ├── checkpoints.py
│       │   └── export.py
│       ├── inference/
│       │   ├── synthesizer.py
│       │   ├── controls.py
│       │   ├── streaming.py
│       │   └── timings.py
│       ├── text/
│       │   ├── normalize.py
│       │   ├── pronunciation.py
│       │   └── languages.py
│       └── service/
│           ├── app.py
│           ├── routes.py
│           ├── schemas.py
│           ├── lifecycle.py
│           └── settings.py
├── scripts/
│   ├── prepare_dataset.py
│   ├── evaluate_baselines.py
│   ├── train.py
│   ├── export_model.py
│   └── run_service.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── audio_quality/
│   └── fixtures/
├── assets/
│   ├── recording-scripts/
│   └── pronunciation/
├── models/
│   └── README.md
├── data/
│   ├── README.md
│   ├── manifests/
│   ├── raw/
│   ├── interim/
│   └── processed/
└── runs/
    └── README.md
```

Repository rules:

- `src/` contains importable production code; `scripts/` are thin entry points.
- Runtime APIs depend on engine interfaces, not a specific TTS implementation.
- Configuration is versioned; secrets and machine-specific paths are not.
- Raw audio, generated audio, checkpoints, and experiment runs are ignored by
  Git. Track only manifests, schemas, small licensed fixtures, and checksums.
- Large artifacts use an explicit artifact store or Git LFS only after policy
  and cost are approved.
- Tests mirror production boundaries and do not require the full model for unit
  tests.

## 7. Implementation phases

### Phase 0 — Governance and measurable requirements

- [ ] Complete consent, provenance, retention, and revocation documents.
- [ ] Write the voice persona and define every control in perceptual terms.
- [ ] Confirm languages, hardware, deployment, and licensing constraints.
- [ ] Create a held-out evaluation script not used in training.
- [ ] Set measurable latency, intelligibility, naturalness, and memory targets.

Exit criteria:

- Consent and permitted-use scope are signed and versioned.
- Hardware and voice-control requirements are testable.
- Evaluation sentences and success thresholds are approved.

### Phase 1 — Foundation and contracts

- [ ] Initialize Git and scaffold the repository structure.
- [ ] Configure Python, dependency locking, linting, formatting, type checking,
  tests, and pre-commit checks.
- [ ] Implement domain schemas for requests, controls, metadata, and errors.
- [ ] Publish an OpenAPI contract and mock streaming service.
- [ ] Add CI for static checks, unit tests, and secret scanning.

Exit criteria:

- A fake engine can stream deterministic fixture audio through the full API.
- Cancellation and validation contract tests pass.
- A fresh checkout can be set up and tested from documented commands.

### Phase 2 — Baseline engine evaluation

- [ ] Shortlist locally deployable TTS engines using primary documentation.
- [ ] Verify licenses for code, base models, generated output, and adaptation.
- [ ] Measure CPU/GPU real-time factor, first-audio latency, RAM/VRAM, size,
  Thai/English quality, streaming, and training support.
- [ ] Test whether each voice control is native, approximated, or unsupported.
- [ ] Record the selected baseline and rejected alternatives in an ADR.

Candidate selection criteria:

- Natural Thai and English output, including code-switching.
- Legal adaptation and local deployment.
- Speaker/style conditioning with minimal identity drift.
- Streaming or chunkable generation.
- Stable export path and active maintenance.

Exit criteria:

- One baseline synthesizes the held-out evaluation set locally.
- License and artifact provenance are documented.
- Latency fits the target interaction budget.

### Phase 3 — Dataset pipeline

- [ ] Publish recording instructions for microphone, room, distance, levels, and
  performance consistency.
- [ ] Design prompts covering phonemes, numbers, dates, names, questions,
  emotions, and Thai/English code-switching.
- [ ] Record separate neutral and controlled-style examples where the selected
  engine supports labeled conditioning.
- [ ] Keep immutable raw recordings separate from derived audio.
- [ ] Normalize sample rate without destructive denoising or compression.
- [ ] Segment utterances and create exact transcripts.
- [ ] Detect clipping, silence, noise, transcript mismatch, and duplicates.
- [ ] Split by utterance and prompt family into train, validation, and held-out
  test sets.
- [ ] Generate a versioned manifest with hashes, consent ID, speaker, language,
  style labels, and processing lineage.

Exit criteria:

- Every clip has consent, transcript, speaker, language, hash, and provenance.
- No evaluation sentence or near-duplicate appears in training.
- Automated quality checks pass; exclusions remain auditable.

### Phase 4 — Training and controllability

- [ ] Establish reproducible configs, random seeds, environment lock, and a
  small end-to-end training smoke test.
- [ ] Train/adapt neutral identity before adding style control.
- [ ] Add supported conditioning for prosody, style, or reference audio.
- [ ] Calibrate public controls to stable internal ranges.
- [ ] Version presets and pronunciation dictionaries independently.
- [ ] Track checkpoints, losses, audio samples, code revision, dataset version,
  configuration, and hardware.
- [ ] Select checkpoints on held-out listening quality, not loss alone.

Exit criteria:

- The selected checkpoint improves over the baseline on predefined metrics.
- Low/neutral/high control samples behave predictably without major identity
  drift or intelligibility loss.
- Training can be reproduced from a manifest and locked configuration.

### Phase 5 — Evaluation and safety

- [ ] Measure Thai character error rate and English word error rate with a
  separate recognizer.
- [ ] Measure speaker consistency without using similarity as the sole metric.
- [ ] Run blinded naturalness, preference, and control-strength listening tests.
- [ ] Test control combinations and boundary values.
- [ ] Test numbers, dates, URLs, abbreviations, code, names, punctuation,
  code-switching, and long sentences.
- [ ] Test abusive input length, Unicode edge cases, cancellation races,
  concurrency, and output exhaustion.
- [ ] Document prohibited use, limitations, and disclosure requirements.

Exit criteria:

- Quality, controllability, latency, and safety thresholds pass.
- Known failure modes appear in the model card.
- The release contains no training recordings or private metadata.

### Phase 6 — Production local service

- [ ] Implement engine loading, health/readiness, and capability discovery.
- [ ] Implement bounded streaming synthesis and request cancellation.
- [ ] Add text normalization and versioned pronunciation dictionaries.
- [ ] Add phoneme/viseme timing where reliable.
- [ ] Add concurrency limits, backpressure, timeouts, and deterministic cleanup.
- [ ] Add structured metrics without synthesis text or personal data.
- [ ] Package for the target OS with reproducible startup configuration.

Exit criteria:

- First audio and real-time factor meet the target on target hardware.
- Cancellation promptly stops computation and audio production.
- Load tests demonstrate bounded memory and predictable rejection.
- The service restarts cleanly and reports exact model/runtime versions.

### Phase 7 — AI assistant integration

- [ ] Add a `local-model` provider behind the AI application's voice interface.
- [ ] Map assistant voice settings to documented styles and controls.
- [ ] Send only sanitized `speechText`, never raw tool output, secrets, code, or
  unreviewed URLs.
- [ ] Stream audio to playback as chunks arrive.
- [ ] Connect visemes to the avatar, with RMS mouth movement as fallback.
- [ ] Implement barge-in by cancelling synthesis and playback with one
  `requestId`.
- [ ] Surface health, capability, model version, and errors in diagnostics.
- [ ] Keep browser speech and hosted TTS as independent fallback providers.

Exit criteria:

- Selecting `local-model` does not change the text/agent provider.
- The AI can select presets and bounded voice controls.
- Interruption, reconnect, mute, fallback, and lip sync pass end-to-end tests.
- Failure of the voice service cannot block or crash the assistant.

### Phase 8 — Release and maintenance

- [ ] Version model, dataset, runtime, presets, and pronunciation data separately.
- [ ] Release checksums, SBOM, model card, licenses, and compatibility metadata.
- [ ] Define rollback, migration, and model/runtime compatibility policies.
- [ ] Monitor latency, failures, clipping, and reported pronunciation issues.
- [ ] Test restore, upgrade, deletion, and consent-revocation procedures.

## 8. Quality gates

Exact targets must be set after hardware confirmation. Initial recommended
gates for interactive local use:

- First audio: target at or below 500 ms; hard ceiling 1,000 ms.
- Real-time factor: below 0.8 at p95 on target hardware.
- Cancellation: compute and output stop within 250 ms after receipt.
- Availability: no process crash during a 30-minute mixed-load test.
- Audio: no clipping; peak below -1 dBFS after final normalization.
- Controls: listeners correctly order low/neutral/high samples above chance,
  without a material intelligibility regression.
- Reproducibility: fixture training and API contract tests pass in CI.

These are provisional, not promises. Record final thresholds in a versioned
evaluation configuration.

## 9. Test strategy

- Unit tests: normalization, schemas, control bounds, manifests, and errors.
- Contract tests: API response, streaming framing, versions, and cancellation.
- Integration tests: fake engine in CI; real engine on a model-enabled runner.
- Dataset tests: hashes, schema, consent reference, audio quality, and leakage.
- Audio regression tests: duration, silence, loudness, clipping, and fixed-seed
  features with tolerant thresholds.
- Perceptual tests: naturalness, identity, pronunciation, and control strength.
- Performance tests: cold/warm latency, real-time factor, load, and memory.
- Security tests: malformed input, path injection, log leakage, and limits.

## 10. Risks and mitigations

- Voice controls may change speaker identity: calibrate narrow ranges and test
  identity at control extremes.
- “Pinched” tone may sound synthetic with DSP: prioritize learned conditioning
  and use DSP only for restrained finishing.
- Thai/English code-switching may be weak: include targeted prompts and score
  each language and mixed utterances separately.
- Streaming may reduce prosody across chunks: synthesize with sentence-aware
  lookahead and validate chunk-boundary artifacts.
- Training may overfit limited recordings: use held-out prompts, early stopping,
  and listening tests.
- Model licenses may block distribution: complete licensing review before data
  collection or adaptation.
- Local hardware may miss latency targets: benchmark before selecting an engine
  and retain quantization/export alternatives.

## 11. First milestone

Deliver before expensive recording or training:

1. Confirmed requirements and target hardware profile.
2. Signed consent and provenance templates.
3. Voice specification with reference descriptions for every control.
4. Scaffolded repository with quality tooling and a fake streaming API.
5. ADR comparing viable local TTS baselines and their licenses.
6. Baseline benchmark report using the held-out evaluation script.

Only approve dataset collection and model adaptation after this milestone passes
review.
