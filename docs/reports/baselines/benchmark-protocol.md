# Local TTS baseline benchmark protocol

Status: protocol only; no measurements recorded  
Config: `configs/evaluation/baselines.toml`

## Reproducibility record

For every run capture OS/build, CPU model and logical cores, RAM, GPU model,
driver, VRAM, power mode, runtime/backend versions, candidate repository and
weight revisions, precision/quantization, model and codec hashes, command,
environment lock hash, project commit, evaluation-manifest hash, and UTC time.
Do not record synthesis text or reference audio in ordinary logs.

Run offline after artifacts are acquired and verified. Disable model/runtime
network access during measurement. Use one process and one concurrent request
unless a scenario says otherwise. Pin configuration; do not tune one candidate
after seeing held-out results without creating a new run ID.

## Evaluation set

Use the approved, immutable held-out manifest with separate strata:

- Thai: short, medium, long, tones, numbers, dates, names, questions;
- English: short, medium, long, numbers, abbreviations, names;
- mixed Thai-English: both switch directions, embedded names/numbers;
- control probes: low/neutral/high only for supported native controls;
- safety: maximum accepted text, Unicode edge cases, and cancellation.

No held-out prompt or near-duplicate may occur in adaptation data. Use the same
consented reference clips, text, seeds where supported, and output sample rate.

## Scenarios

For each candidate/backend/device:

1. cold process start, model load, and first synthesis;
2. five warmups excluded from statistics;
3. three measured repetitions per utterance in deterministic shuffled order;
4. streaming response consumed at real playback rate and at a deliberately
   slow rate;
5. cancellation at 100 ms, after first audio, and halfway through predicted
   duration;
6. 30-minute mixed-load soak at configured concurrency;
7. native/default precision, then one officially supported quantized variant
   only if the native variant misses a resource gate.

Whole-result engines must be labeled `buffered`; writing an already-complete
array in chunks is not streaming.

## Metrics

Measure with monotonic clocks:

- process start to readiness;
- request receipt to first playable audio byte (cold and warm);
- synthesis wall time, audio duration, and real-time factor;
- cancellation receipt to final model work and final output;
- peak process RSS, peak allocated/reserved VRAM, model artifact size;
- output sample rate, duration, peak dBFS, clipping, silence, and chunk-boundary
  discontinuity;
- Thai CER, English WER, and mixed-language CER/WER components;
- failure, timeout, retry, incomplete-stream, and crash counts.

Report median, p95, maximum, sample count, and raw per-utterance records. GPU
timing must synchronize the device around measured regions. Measure first
audio at the consumer boundary, not when the model creates its first tensor.

Listening review is blinded and randomized. Score naturalness,
intelligibility, pronunciation, speaker consistency, code-switching, chunk
artifacts, and supported-control ordering. Speaker similarity is supporting
evidence, never the sole quality metric.

## Gates

The candidate must:

- support Thai, English, and mixed inputs at acceptable held-out quality;
- pass license/provenance review for local inference and intended adaptation;
- achieve warm first audio p95 at or below 500 ms (hard ceiling 1,000 ms);
- achieve RTF p95 below 0.8;
- stop compute/output within 250 ms p95 after cancellation;
- remain bounded and crash-free in the soak test;
- emit no clipped samples and remain below -1 dBFS after normalization;
- expose only measured, monotonic controls without material intelligibility or
  identity regression.

Targets are provisional until target hardware is approved. Record any approved
change as an ADR/config revision before rerunning.

## Result format

Write a machine-readable result per candidate/run outside Git artifact paths
and a redacted summary under `docs/reports/baselines/`. Each claim is labeled
`measured`, `publisher_reported`, or `not_tested`. Never merge publisher
numbers into measured aggregates.

## CI/CD acceptance

Ordinary CI does not download models. It must parse the TOML config, reject
unknown candidate/status/control values, require immutable revision fields,
validate unique IDs and scenario references, and ensure every candidate has
official source and license URLs. Fixture tests use a fake engine to validate
metric math and result-schema handling.

Model-enabled benchmark jobs run only in a protected environment with approved
artifact access. They emit checksummed raw results, configuration, environment
metadata, and a signed summary. Promotion is blocked if config validation,
provenance review, any hard gate, or result attestation fails. Benchmark
artifacts never contain reference audio or full prompt text.

