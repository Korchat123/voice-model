# ADR 0000: Target hardware and interaction budget

- Status: **Proposed — USER INPUT REQUIRED**
- Date: `USER_INPUT_REQUIRED`
- Decision owners: `USER_INPUT_REQUIRED`

## Context

Engine selection, export format, concurrency, and quality targets depend on a
specific deployment machine. Results from other hardware are evidence, not
acceptance.

## Required target profile

| Field | Decision |
|---|---|
| Operating system and version | `USER_INPUT_REQUIRED` |
| CPU model, core/thread count | `USER_INPUT_REQUIRED` |
| GPU/accelerator and driver/runtime | `USER_INPUT_REQUIRED` |
| RAM and available budget | `USER_INPUT_REQUIRED` |
| VRAM and available budget | `USER_INPUT_REQUIRED` |
| Storage type and available budget | `USER_INPUT_REQUIRED` |
| Power/thermal mode | `USER_INPUT_REQUIRED` |
| Deployment package/container | `USER_INPUT_REQUIRED` |
| Concurrent synthesis streams | `USER_INPUT_REQUIRED` |

## Proposed measurable budget

These are provisional values from the project plan, not approved guarantees:

| Measure | Proposed target | Measurement rule |
|---|---:|---|
| First audio, warm p95 | ≤ 500 ms | Request accepted to first playable PCM byte |
| First audio, hard ceiling | ≤ 1,000 ms | No accepted interactive request exceeds it |
| Real-time factor, p95 | < 0.80 | Synthesis wall time / produced audio duration |
| Cancellation, p95 | ≤ 250 ms | Cancel receipt to compute and output stop |
| Mixed-load stability | 30 min, no crash | Approved `th`/`en`/`mixed` request distribution |
| Peak output | < -1 dBFS | Measured after final normalization |

Benchmark cold start separately from warm requests. Record text set version,
model/runtime versions, configuration hash, hardware telemetry, sample count,
median, p95, maximum, and failures. Report Thai, English, and mixed-language
results separately.

## Decision

`USER_INPUT_REQUIRED`

No baseline may be declared accepted and no expensive recording/training may
start until the target profile, measurement protocol, and final thresholds are
approved.

## Consequences

The chosen baseline must pass on this exact hardware profile. If it does not,
the team must change model/export settings, revise the hardware decision, or
explicitly approve a different interaction budget in a superseding ADR.

## Approval

- Hardware owner: `USER_INPUT_REQUIRED`
- Product owner: `USER_INPUT_REQUIRED`
- Approved date/version: `USER_INPUT_REQUIRED`
