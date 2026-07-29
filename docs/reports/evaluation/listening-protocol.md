# Blinded listening protocol

Status: required before model release

Use consented listeners who understand the study and data-retention terms.
Randomize sample order and replace engine/model names with opaque IDs. The
person preparing the key must not participate in scoring. Loudness-normalize
only with the same documented process for every candidate; retain original
files outside Git.

Evaluate Thai, English, and mixed Thai-English separately. Balance short,
medium, and long prompts, speakers, prompt families, and control levels. Never
use training prompts. Include hidden repeat samples to estimate listener
consistency and a consented natural reference where permitted.

Listeners score:

- naturalness and absence of artifacts;
- intelligibility and pronunciation;
- speaker consistency, without being asked to identify a person;
- code-switch accuracy;
- chunk-boundary continuity;
- perceived control strength for randomized low/neutral/high triples.

For each control triple, ask for ordering before preference. A control passes
only when ordering is above the pre-registered chance threshold and neither
intelligibility nor speaker consistency materially regresses. Evaluate
resonance as “pinched/nasal” to “open/full”; do not expose implementation
labels or expected answers.

Pre-register sample count, listener count, exclusion rules, thresholds, and
analysis before revealing the key. Report counts, uncertainty intervals,
ties, exclusions, and all failed comparisons. Do not report only preferred
examples.

Store response data under pseudonymous IDs. Do not commit listener identity,
reference audio, generated audio, or free-text comments containing personal
data. Publish a redacted aggregate and immutable config/result hashes.

ASR error rates and speaker metrics require separately approved adapters with
recorded model revisions. They supplement this listening study and cannot
replace it. Missing dependencies must produce `not_measured`, never a zero,
null-as-success, or fabricated score.

The standard-library `IntelligibilityProxy` reports characters per second and
voiced milliseconds per character to catch gross truncation, silence, or rate
anomalies. It is explicitly a sanity proxy, not CER/WER or a claim that speech
was understood.

## CI phase gate

Ordinary CI parses `configs/evaluation/evaluation.toml`, unit-tests metric
math/report validation, and runs audio-quality tests on generated fixtures.
It must reject release reports containing unset revisions, required
`not_measured` metrics, clipping over the configured maximum, or failed hard
latency/cancellation gates.

Model-enabled evaluation runs only in a protected environment. The job records
artifact/config/environment revisions and publishes checksummed reports.
Human listening sign-off and approved ASR/speaker adapter results remain manual
protected-environment approvals; ordinary CI must not download those models.
