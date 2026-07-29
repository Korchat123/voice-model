# Voice-control calibration report

- Status: `unmeasured | measured-not-approved | approved | rejected`
- Engine ID and immutable revision:
- Calibration config version and hash:
- Dataset/evaluation-manifest revision:
- Evaluator and approval record:

No control may appear in production capabilities while this report is
`unmeasured` or `measured-not-approved`.

## Per-control evidence

For each supported control record:

- public levels and mapped engine values;
- Thai, English, and mixed-language sample counts;
- objective proxy values with uncertainty;
- blinded low/neutral/high ordering results;
- intelligibility and speaker-consistency deltas;
- clipping, loudness, and artifact failures;
- interactions with every other approved control;
- decision, rationale, and evidence artifact hashes.

For resonance, evaluate the ordered perceptual labels
`pinched/nasal -> calibrated neutral -> open/full`. Record identity drift and
intelligibility separately. An audible change alone is insufficient approval.

## Approval gates

- Mapping anchors are bounded and monotonic.
- Every non-neutral mapping is measured and explicitly approved.
- Neutral fallback is verified safe for the exact engine revision.
- Unsupported controls are absent from capabilities and non-neutral requests
  fail explicitly.
- Blinded ordering exceeds the pre-registered threshold.
- Intelligibility, identity, latency, and audio-quality regressions remain
  within approved thresholds.

## CI phase gate

CI parses preset, mapping, and control-evaluation configs; tests interpolation,
bounds, approval gates, capability filtering, and unsupported behavior. It
must reject `approved = true` with unset evidence or unmeasured status.
Perceptual approval remains a protected manual gate and is never inferred from
CI success.
