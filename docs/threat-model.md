# Local voice service threat model

> Status: initial hardening model for the fake-engine service. Reassess whenever
> a real model adapter, remote binding, authentication, file access, assistant
> integration, or deployment packaging is added.

## Assets and security goals

Protect:

- voice owner consent, identity, recordings, transcripts, and provenance;
- synthesis text, generated audio, model weights, pronunciation data, and logs;
- local filesystem, credentials, processes, memory, CPU/GPU, and availability;
- model/runtime identity and the integrity of cancellation and request limits.

The service must synthesize only the bounded text supplied, return only declared
audio/metadata, and avoid exposing text or private data through errors or logs.

## Trust boundaries

1. An untrusted local client sends HTTP method, path, headers, and JSON.
2. The transport parses bytes into the versioned domain request.
3. Validated requests enter bounded admission and cancellation lifecycle state.
4. An engine adapter receives text and produces chunks inside the process.
5. Diagnostics and metrics cross into logs/monitoring.
6. Model and configuration artifacts enter from deployment storage.

The current default is loopback, but loopback clients are not automatically
trusted: browser processes, extensions, compromised local applications, and
cross-origin requests may still be hostile. Remote binding materially changes
the threat model and requires authentication, authorization, TLS, origin policy,
rate limits, and deployment review.

## Threats and required controls

| Threat | Control and verification |
|---|---|
| Oversized text, UTF-8 expansion, or predicted output exhaustion | Enforce character, byte, duration, concurrency, queue, and timeout limits before expensive work; test boundary and over-limit input |
| Malformed JSON, type confusion, unknown fields, NaN/control abuse | Strict schema/domain validation and stable non-reflective errors |
| Path traversal or file/URI injection through text, voice, preset, or request ID | Never interpret request fields as paths; restrict identifiers; test traversal, encoded separators, drive paths, UNC paths, URLs, and NUL-like input |
| Duplicate IDs and cancellation races | Atomic admission, conflict response, idempotent cancellation, prompt resource cleanup, bounded tombstones |
| Queue or concurrent request denial of service | Bounded active/queued states, deterministic `429`, retry guidance, timeouts, load tests, and memory observation |
| Sensitive synthesis text in responses or logs | Do not log bodies/text; sanitize validation details; test response, captured logs, exceptions, and access-log configuration |
| Malicious/buggy engine exception leaks text | Catch errors with a constant public response and sanitize exception logging; never rely on an engine to avoid embedding text |
| Model substitution or unapproved voice loading | Pin model/engine IDs, versions, hashes, license and consent approvals; expose exact identity |
| Network exposure and browser-driven requests | Loopback default; explicit remote opt-in; authentication/TLS/origin controls before remote deployment |
| Dependency or workflow compromise | Locked dependencies, pinned actions, least privilege, scans, immutable release checksums and attestations |

## Current findings

Detailed evidence belongs in `docs/reports/security/`. At this stage:

- request validation, response envelopes, request IDs, queue limits, and
  loopback configuration have automated coverage;
- security/load tests use the deterministic fake engine and contain no voice
  recordings or model artifacts;
- engine exception logging needs special care because Python traceback messages
  can contain attacker-controlled synthesis text; this is tracked by an
  expected-failure regression test until the service owner implements sanitized
  exception logging;
- authentication, CORS/origin policy, TLS, process isolation, operating-system
  permissions, and real model resource bounds remain deployment work.

## Release gate

Before release, remove every strict expected failure, run security and load
tests on the exact release artifact, inspect logs and package contents, verify
bounded memory on target hardware, and obtain privacy/security approval.
