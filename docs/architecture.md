# Architecture

## Boundaries

The local voice service turns already-sanitized text into bounded audio. It
does not own conversation state, tool execution, credentials, playback, or
arbitrary files. The assistant remains responsible for deciding what may be
spoken and for cancelling playback during barge-in.

```text
AI assistant
  -> versioned HTTP adapter
  -> validation, admission, lifecycle
  -> synthesis domain service
  -> engine protocol
  -> selected local TTS adapter
  -> bounded PCM stream
```

Dependencies point inward: HTTP schemas map to transport-neutral domain
requests; the synthesis service depends on an engine protocol; engine adapters
depend on vendor runtimes. Voice controls, lifecycle state, and errors are
domain concepts and must not import the web framework.

## Request lifecycle

A request moves through `validating -> queued -> running -> completed`,
`cancelled`, `timed_out`, or `failed`. The request registry owns uniqueness,
deadlines, cancellation tokens, and short-lived terminal tombstones. Admission
occurs only after complete validation and predicted-output limit checks.

Backpressure is explicit: one configurable active-request semaphore and a
bounded queue. No unbounded task, text, audio, or log buffer is permitted.
Audio chunks flow through a bounded channel so a slow/disconnected client
stalls and then cancels engine production rather than accumulating memory.

Cancellation by `DELETE`, timeout, shutdown, or client disconnect sets the
same token. Engine adapters poll or await it between bounded generation steps,
release device and host buffers in `finally`, and stop emitting chunks.

## Configuration and versioning

Safe defaults are versioned under `configs/`. Secrets, machine paths, model
weights, and local overrides are environment/runtime concerns. Presets conform
to `configs/inference/preset.schema.json` and carry their own semantic version.
`configs/inference/service.example.toml` records loopback, audio, privacy, and
resource-limit defaults; a deployment may tighten limits but must not weaken
them without an explicit security review.
The API, runtime, model, preset collection, pronunciation data, and dataset are
versioned independently.

At startup the service validates all preset data and engine capability
mappings. A preset referencing an unsupported control prevents readiness; it
is not partially applied. Capabilities are generated from the active adapter
plus validated configuration.

## Privacy and security

The listener defaults to loopback. Remote exposure is an operator decision
requiring an authenticated, encrypted boundary. The API accepts text and
enumerated identifiers only—never paths, URLs, shell fragments for execution,
or reference-audio uploads. Structured telemetry records IDs, counts,
versions, status, and duration but not full text or audio.

## Delivery architecture

Pull-request CI performs static analysis, tests, schema/contract validation,
secret scanning, and compatibility checks. The main branch builds one
checksummed immutable runtime artifact and SBOM. A fake-engine smoke deployment
must pass before that artifact can be promoted. Model-enabled runners and
target-hardware performance jobs are protected environments because model
artifacts, licenses, and hardware are not assumed available to ordinary CI.

Rollback selects a previously validated immutable artifact and compatible
model/preset tuple. Runtime startup fails readiness on incompatibility rather
than attempting an implicit migration.
