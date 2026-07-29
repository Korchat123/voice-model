# Engine adapter configuration

The example registry contains one deterministic test adapter and one inert
placeholder for the provisional MOSS benchmark candidate. A pending adapter
must not be instantiated. Its capabilities remain empty until the benchmark,
license, artifact, and governance approvals are recorded.

Runtime loading rules:

- only factories below `voice_model.engines.adapters` are accepted;
- only an `approved` adapter may serve real synthesis;
- `test-only` adapters require an explicit test/development mode;
- `pending` and `rejected` adapters fail closed;
- configured model identity and immutable artifact revision must match the
  adapter's runtime report;
- configured controls must be a subset of runtime-reported controls;
- unknown or unsupported controls are errors and are never discarded;
- adapter settings cannot contain secrets, URLs, or filesystem paths.

Production configuration must be copied into deployment configuration and
validated before startup. This example is not production approval.

