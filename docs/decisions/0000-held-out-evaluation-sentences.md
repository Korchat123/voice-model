# Held-out evaluation sentence specification

- Status: **Proposed — SENTENCE SET AND THRESHOLDS REQUIRE APPROVAL**
- Dataset role: evaluation only; prohibited from train and validation inputs

## Purpose

Create a versioned, access-controlled sentence set that measures intelligibility,
pronunciation, prosody, code-switching, controllability, and difficult text
without leaking exact prompts into training.

## Coverage matrix

Each release of the set must identify unique prompt IDs and include:

| Category | Thai | English | Mixed |
|---|---:|---:|---:|
| Short statements | required | required | required |
| Questions and exclamations | required | required | required |
| Long and multi-clause sentences | required | required | required |
| Numbers, decimals, money, dates, times | required | required | required |
| Names, places, abbreviations, technical terms | required | required | required |
| Ambiguous pronunciation/context | required | required | required |
| Control-balanced carrier sentences | required | required | required |
| Unicode and punctuation edge cases | required | required | required |

Mixed prompts must cover Thai-to-English and English-to-Thai transitions,
intra-sentence switches, proper nouns, spelled tokens, and technical phrases.
Use prompt families to detect paraphrase and near-duplicate leakage.

## Record schema

Each sentence record must contain:

- `prompt_id`, `set_version`, `language_mode`, and `prompt_family_id`;
- exact NFC-normalized text and a SHA-256 digest;
- category and required phenomena tags;
- expected reading or pronunciation notes;
- source/author and license;
- review status for Thai and/or English as applicable;
- `allowed_splits: ["held_out"]`; and
- sensitivity classification with access restrictions.

## Isolation and validation

- Store exact prompts outside public documentation if secrecy reduces overfit.
- Compare normalized text, hashes, token n-grams, and prompt-family IDs against
  train and validation manifests before every run.
- Fail dataset acceptance when an exact or near duplicate crosses splits.
- Never tune pronunciation, presets, checkpoints, or stopping decisions using
  the final acceptance subset; use a separate development set.
- Record additions as a new immutable version; do not silently edit prompts.

## Evaluation protocol

Synthesize every prompt at neutral settings. Use a balanced subset for each
supported control at low, neutral, high, boundaries, and approved combinations.
Randomize/blind listening samples. Report Thai CER, English WER, mixed-language
segment results, naturalness, pronunciation, identity consistency, artifacts,
latency, and control ordering separately.

Exact counts, sentence text, recognizer versions, listener sample size,
acceptance thresholds, and reviewers are `USER_INPUT_REQUIRED`.

## Approval gate

- Language reviewers: `USER_INPUT_REQUIRED`
- Dataset/governance reviewer: `USER_INPUT_REQUIRED`
- Evaluation owner: `USER_INPUT_REQUIRED`
- Approved set version and manifest hash: `USER_INPUT_REQUIRED`
