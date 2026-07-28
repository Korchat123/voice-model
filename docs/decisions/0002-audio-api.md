# ADR 0002: Versioned HTTP audio API

- Status: Accepted for Phase 1
- Date: 2026-07-29

## Context

The assistant needs low-latency local audio, capability discovery, predictable
voice controls, and prompt barge-in. The synthesis domain must remain usable
behind a future WebSocket or gRPC transport. The boundary must also be easy to
mock and test without a model.

## Decision

Use a `/v1` HTTP API with health, capabilities, synthesis, and idempotent
cancellation endpoints. Stream raw 24 kHz mono signed 16-bit little-endian PCM
as the primary representation. Put immutable synthesis identity in headers and
optional terminal metadata in a base64url JSON trailer. Offer WAV only as a
bounded, completed debug response.

Use one caller-generated request ID across synthesis, cancellation, playback,
and diagnostics. A shared cancellation token handles explicit cancellation,
disconnect, timeout, and shutdown. Validate the whole request before model
admission. Reject unsupported controls and features explicitly.

Public controls are normalized to `[-1, 1]`, with zero meaning calibrated
neutral. Named presets are schema-validated, independently versioned data;
explicit controls override preset keys.

## Consequences

HTTP is widely supported and easy to test and proxy. Raw PCM permits playback
before synthesis completes and avoids container-finalization ambiguity.
Clients must handle arbitrary byte chunking and cannot depend on trailers.
Timing metadata is available only from engines that can produce it reliably.

Cancellation is a second HTTP request and therefore has a small race with
already-emitted audio. Keeping playback cancellation in the assistant is still
necessary. If bidirectional events or richer timing become essential, a
WebSocket or gRPC adapter may be added without changing domain requests or the
engine protocol.

## Alternatives considered

- WebSocket: richer bidirectional events, but more connection state and
  reconnect complexity than Phase 1 requires.
- gRPC: strong streaming schemas, but adds client/tooling constraints for a
  local assistant.
- Streaming WAV: familiar format, but container length/finalization and
  concatenation behavior complicate interrupted streams.
- JSON/base64 audio frames: self-describing, but increases bandwidth, copying,
  parsing, and latency.

## Compliance

Contract and privacy tests are release gates. The service defaults to loopback,
does not accept filesystem paths, and does not log text by default. Deployment
promotion requires the CI/CD acceptance checks in `docs/api.md`.

