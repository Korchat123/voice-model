# Initial service hardening report

- Scope: current local ASGI service with deterministic fake engine
- Data: generated request strings only; no recordings or private model
- Status: initial hardening checks pass; known privacy defect resolved

## Checks added

- malformed JSON roots, missing fields, invalid types, Unicode byte expansion,
  unknown fields, non-finite controls, and oversized requests;
- encoded traversal and filesystem/URI-shaped values in identifiers and text;
- response and normal validation log non-disclosure;
- bounded repeated-request output;
- lifecycle active/queue rejection and recovery under concurrent load;
- explicit regression coverage for exception-log disclosure.

## Resolved finding SEC-001: engine exceptions disclosed synthesis text in logs

- Severity: high when logs leave the process or are accessible to other users
- State: resolved
- Original evidence: exception traceback logging included an engine exception
  message that embedded request text.
- Resolution: the route logs a constant message and safe request identifier
  without exception details or traceback content.
- Regression: the required `test_engine_exception_logs_are_text_free` check
  demonstrates that the response and captured application logs contain none of
  the sentinel speech text.

## Limitations

These tests are functional scaffolding, not a penetration test. They do not yet
measure process RSS/VRAM, real-engine cancellation latency, network
authentication, TLS, browser-origin behavior, operating-system sandboxing, or
multi-process deployment.
