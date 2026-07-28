# Local voice HTTP API

Status: Phase 1 contract  
API version: `v1`

This document is normative for the public HTTP boundary. The service binds to
`127.0.0.1` by default. Remote binding requires explicit operator
configuration and authentication at a trusted reverse proxy.

## Common rules

- All JSON uses UTF-8 and `Content-Type: application/json`.
- Clients send `X-Request-ID`; it must equal the synthesis `request_id`.
- IDs are 1-64 characters matching `^[A-Za-z0-9][A-Za-z0-9._:-]*$`.
- Unknown JSON fields, unknown controls, non-finite numbers, and values outside
  their declared range are rejected; they are never silently ignored.
- No endpoint accepts input paths, output paths, URLs, or reference audio.
- API compatibility is expressed by the `/v1` path. Model, runtime, preset,
  and pronunciation versions are independent and returned in capabilities and
  synthesis metadata.
- Full input text is excluded from logs and metrics by default. A keyed request
  ID, text length, language, status, and latency may be logged.

## `GET /v1/health`

Returns liveness and readiness without echoing configuration or private data.
HTTP `200` means the process is live. `ready` determines whether synthesis may
be accepted.

```json
{
  "status": "ok",
  "ready": true,
  "runtime_version": "0.1.0",
  "model_loaded": true
}
```

## `GET /v1/capabilities`

Returns only controls actually implemented by the active engine.

```json
{
  "api_version": "v1",
  "runtime_version": "0.1.0",
  "model": {"id": "fake-local", "version": "1"},
  "voices": ["primary"],
  "languages": ["th", "en", "auto"],
  "encodings": ["pcm_s16le", "wav"],
  "streaming_encodings": ["pcm_s16le"],
  "sample_rates_hz": [24000],
  "controls": {
    "pitch": {"minimum": -1.0, "maximum": 1.0, "default": 0.0},
    "pace": {"minimum": -1.0, "maximum": 1.0, "default": 0.0},
    "energy": {"minimum": -1.0, "maximum": 1.0, "default": 0.0},
    "warmth": {"minimum": -1.0, "maximum": 1.0, "default": 0.0},
    "brightness": {"minimum": -1.0, "maximum": 1.0, "default": 0.0},
    "breathiness": {"minimum": -1.0, "maximum": 1.0, "default": 0.0},
    "resonance": {"minimum": -1.0, "maximum": 1.0, "default": 0.0},
    "expressiveness": {"minimum": -1.0, "maximum": 1.0, "default": 0.0}
  },
  "presets": [
    {"id": "neutral", "version": "1.0.0"},
    {"id": "warm", "version": "1.0.0"}
  ],
  "limits": {
    "max_text_characters": 2000,
    "max_utf8_bytes": 8000,
    "max_predicted_audio_ms": 120000,
    "request_timeout_ms": 130000,
    "max_concurrent_requests": 1,
    "max_queued_requests": 2,
    "cancel_target_ms": 250
  },
  "timings": {"phonemes": false, "visemes": false}
}
```

Clients must feature-detect controls and timings. A missing control is
unsupported, not equivalent to neutral.

## `POST /v1/synthesis`

Request:

```json
{
  "request_id": "turn-018",
  "text": "สวัสดี, welcome back.",
  "language": "auto",
  "voice": "primary",
  "preset": "warm",
  "controls": {
    "pace": -0.1,
    "resonance": 0.2
  },
  "seed": 42,
  "encoding": "pcm_s16le",
  "sample_rate_hz": 24000,
  "return_timings": false
}
```

Required fields are `request_id`, `text`, `language`, and `voice`. `language`
is `th`, `en`, or `auto`. `encoding` defaults to `pcm_s16le`;
`sample_rate_hz` defaults to the server's preferred rate. `seed` is an
unsigned 32-bit integer. `return_timings` defaults to false.

All controls are numbers in `[-1.0, 1.0]`; zero is calibrated neutral.
`resonance < 0` means more pinched/nasal and `resonance > 0` means more
open/full. Explicit controls override the selected preset by key. If no preset
is supplied, `neutral` is used. The resolved values are returned as
`applied_controls`.

### Streaming success

For `pcm_s16le`, HTTP `200` uses chunked transfer:

```text
Content-Type: audio/L16;rate=24000;channels=1
X-Request-ID: turn-018
X-API-Version: v1
X-Model-ID: fake-local
X-Model-Version: 1
X-Runtime-Version: 0.1.0
X-Preset-ID: warm
X-Preset-Version: 1.0.0
X-Audio-Encoding: pcm_s16le
X-Audio-Sample-Rate: 24000
X-Audio-Channels: 1
Trailer: X-Synthesis-Metadata
```

The body contains contiguous little-endian signed 16-bit mono samples.
Arbitrary HTTP chunk boundaries do not represent audio-frame or sentence
boundaries. A client must tolerate fragmented samples by retaining one trailing
byte until the next chunk. The server sends no JSON in the audio body.

`X-Synthesis-Metadata`, when trailer support is available, is base64url-encoded
UTF-8 JSON:

```json
{
  "request_id": "turn-018",
  "duration_ms": 1820,
  "applied_controls": {
    "pitch": 0.0,
    "pace": -0.1,
    "energy": 0.0,
    "warmth": 0.25,
    "brightness": -0.1,
    "breathiness": 0.0,
    "resonance": 0.2,
    "expressiveness": 0.0
  },
  "phonemes": [],
  "visemes": [],
  "completed": true
}
```

Clients must not require trailers for playback. When reliable timing metadata
is unavailable, timing arrays are omitted. If the connection ends before a
successful trailer, clients treat the audio as incomplete.

`wav` returns `Content-Type: audio/wav` after the bounded result is complete
and is intended for debugging, not low-latency streaming.

### Validation and admission

The server validates the complete request before allocating model work.
Whitespace-only text is invalid. Text is checked against both Unicode
character and UTF-8 byte limits. Unsupported voice, language, encoding,
sample rate, preset, control, or timing requests fail rather than degrade
silently. Requests predicted to exceed the audio-duration limit are rejected.
When the active and queue limits are exhausted, the server returns `429` with
`Retry-After`.

## `DELETE /v1/synthesis/{request_id}`

Cancellation is idempotent. The path ID uses the same validation rules as a
request ID.

- `202`: cancellation was requested for active or queued work.
- `204`: the request was already complete, cancelled, or unknown.

Both outcomes are successful and reveal no cross-request details. Once
accepted, the service stops model work, closes the stream, and releases its
buffers with a target of 250 ms. A race may allow already-written bytes to
arrive. The final trailer, if writable, has `"completed": false` and
`"cancelled": true`. Reusing a request ID while it is active or retained in
the idempotency window returns `409 REQUEST_ID_CONFLICT`.

Disconnecting a synthesis response is treated as an implicit cancellation.
Explicit `DELETE` remains recommended for deterministic barge-in.

## Error envelope

Errors before streaming starts are JSON:

```json
{
  "error": {
    "code": "CONTROL_OUT_OF_RANGE",
    "message": "A request field is invalid.",
    "request_id": "turn-018",
    "details": [
      {"field": "controls.pace", "reason": "must be between -1.0 and 1.0"}
    ],
    "retryable": false
  }
}
```

Messages do not echo text or rejected secret-like values. Stable codes:

| HTTP | Code | Meaning |
|---:|---|---|
| 400 | `INVALID_REQUEST` | Malformed JSON, unknown field, invalid ID, or blank text |
| 400 | `UNKNOWN_CONTROL` | Control name is not in current capabilities |
| 400 | `CONTROL_OUT_OF_RANGE` | Control value is non-finite or outside its range |
| 400 | `LIMIT_EXCEEDED` | Text, predicted audio, or other request limit exceeded |
| 404 | `VOICE_NOT_FOUND` | Requested voice is unavailable |
| 409 | `REQUEST_ID_CONFLICT` | Request ID is already active or retained |
| 415 | `UNSUPPORTED_ENCODING` | Encoding/sample-rate combination is unavailable |
| 422 | `UNSUPPORTED_CAPABILITY` | Language, preset, timing, or feature is unsupported |
| 429 | `CAPACITY_EXCEEDED` | Concurrency and queue are full |
| 500 | `SYNTHESIS_FAILED` | Non-retryable engine failure |
| 503 | `NOT_READY` | Model unavailable or service draining |
| 504 | `SYNTHESIS_TIMEOUT` | Request deadline expired |

After response headers are sent, HTTP status cannot change. The service closes
the audio stream and records a privacy-safe terminal error metric. Clients
treat a missing successful trailer as incomplete and may retry with a new
request ID only when their application policy permits duplicate speech.

## Phase acceptance in CI/CD

Phase 1 cannot deploy unless these contract checks pass:

- the OpenAPI document (when generated) validates and has no unreviewed
  breaking diff against the committed `v1` contract;
- request examples and preset files validate against their schemas;
- contract tests cover unknown fields, unknown controls, range boundaries,
  non-finite values, all limit errors, capacity rejection, and path-shaped
  fields;
- deterministic fake-engine tests verify byte framing, headers, versions,
  stream truncation detection, timeout, disconnect, and idempotent cancellation;
- privacy tests assert input text is absent from default logs and errors;
- lint, format, type, unit, contract, dependency, and secret scans pass.

Deployment uses an immutable artifact produced by CI, not a rebuild. A smoke
job starts it on loopback with the fake engine and exercises health,
capabilities, synthesis, and cancellation. Production/model-enabled deployment
remains gated until target-hardware latency and licensing approvals pass.

