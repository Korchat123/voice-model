# Voice specification

> Status: **DRAFT — VOICE OWNER AND PRODUCT REVIEW REQUIRED**
>
> Values below define testable contracts, not claims about a trained voice.

## Identity and intended character

- Voice ID: `USER_INPUT_REQUIRED`
- Voice owner/authority consent ID: `USER_INPUT_REQUIRED`
- Intended applications and audience: `USER_INPUT_REQUIRED`
- Age presentation, accent, dialect, and regional cues: `USER_INPUT_REQUIRED`
- Character adjectives with concrete audio references: `USER_INPUT_REQUIRED`
- Characteristics that must not be imitated: `USER_INPUT_REQUIRED`
- Neutral reference recording IDs: `USER_INPUT_REQUIRED`

## Language requirements

Working assumption pending approval:

| Mode | Required | Test contract |
|---|---:|---|
| Thai (`th`) | Yes | Native Thai sentences, numbers, dates, names, questions, and punctuation |
| English (`en`) | Yes | English sentences, numbers, abbreviations, names, and questions |
| Thai/English code-switching (`mixed`) | Yes | Both switch directions, intra-sentence switches, names and technical terms |
| Automatic language selection (`auto`) | Yes | Reports detected/selected language; never silently drops text |

User must confirm accent targets, transliteration behavior, pronunciation
authority, and whether other languages are rejected or pronounced best-effort.
Evaluation results must be reported separately for `th`, `en`, and `mixed`.

## Public control contract

All numeric controls use `[-1.0, 1.0]`; `0.0` is the calibrated neutral voice.
Inputs outside the range are rejected rather than clipped. A control is exposed
only when the engine can report it as supported and perceptual tests pass.

| Control | `-1.0` perceptual anchor | `0.0` neutral | `+1.0` perceptual anchor | Safety/identity constraint |
|---|---|---|---|---|
| `pitch` | lower perceived F0 | reference pitch | higher perceived F0 | Preserve natural register; no chipmunk/booming artifacts |
| `pace` | slower articulation | reference pace | faster articulation | Do not pitch-shift; preserve pauses and intelligibility |
| `energy` | gentler intensity | reference effort | stronger intensity | No clipping, shouting, pumping, or unstable loudness |
| `warmth` | cooler/leaner timbre | reference color | warmer/darker timbre | Must remain distinct from pitch and loudness |
| `brightness` | darker spectral balance | reference balance | brighter spectral balance | Avoid hiss, harshness, and muffling |
| `breathiness` | firmer/less airy | reference phonation | airier phonation | Avoid whisper-only output and lost consonants |
| `resonance` | more pinched/nasal | reference resonance | more open/full | Avoid caricature, formant instability, or identity drift |
| `expressiveness` | restrained variation | reference variation | broader prosodic variation | Meaning and punctuation remain faithful |

`style` is a versioned named preset composed from supported controls. Initial
candidate names are `neutral`, `warm`, `cheerful`, `serious`, and `thinking`;
none is approved until its exact values and listening evidence are recorded.

## Control acceptance tests

For every supported control:

- synthesize low, neutral, and high samples using the same held-out prompts and
  seed where supported;
- require listeners to order the intended effect above chance;
- verify intelligibility, loudness, clipping, identity, and artifact metrics;
- test boundary values and representative two-control combinations;
- reject mappings with reversals, dead zones, or material identity drift; and
- publish the engine/model/version and applied values with results.

User must approve numerical thresholds after target hardware and baseline
measurements. Until then, no control is production-supported.

## Output and interaction requirements

Working assumptions pending approval:

- 24 kHz, mono, signed 16-bit little-endian PCM streaming;
- WAV only for bounded debugging/export;
- one local assistant and one concurrent synthesis stream;
- deterministic seed where supported;
- optional phoneme/viseme timing only when reliability is measured;
- cancellation target at or below 250 ms after receipt.

The service must bind to loopback by default, avoid logging full text, reject
filesystem paths, enforce input/output limits, and identify model/runtime
versions in metadata.

## Approval record

- Voice owner review: `USER_INPUT_REQUIRED`
- Product review: `USER_INPUT_REQUIRED`
- Governance review: `USER_INPUT_REQUIRED`
- Approved specification version/date: `USER_INPUT_REQUIRED`
