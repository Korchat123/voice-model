# ADR 0001: Provisional local TTS baseline

- Status: Proposed; target-hardware benchmark required
- Date: 2026-07-29
- Evidence reviewed: 2026-07-29

## Context

The baseline must run locally, synthesize Thai and English (including mixed
text), support a consented voice, and be adaptable behind the repository's
streaming API. License, model artifacts, generated output, adaptation,
latency, memory, and controls must all be evaluated before selection.

No model was downloaded or executed for this ADR. Every performance number
below is a publisher result, not a project measurement.

## Decision

Benchmark **MOSS-TTS-Local-Transformer v1.5** first, with
**JaiTTS-F5TTS** as the Thai-focused quality and lightweight comparator.
Do not approve either for production or training until the protocol in
`docs/reports/baselines/benchmark-protocol.md` passes on target hardware and
artifact/license provenance is signed off.

MOSS is the provisional integration baseline because its official project
documents Thai and English among 31 languages, multilingual/code-switched
synthesis, voice cloning, fine-tuning tutorials, local inference, and
streaming backends. Its model family is documented as Apache-2.0. The 4B local
checkpoint may still miss the project's latency or memory budget, and its
documented controls do not directly implement the project's normalized
warmth, brightness, breathiness, resonance, or expressiveness controls.

JaiTTS-F5TTS is not the default because its official model card calls it a
research prototype released for research and benchmarking. It is useful as a
Thai zero-shot voice-cloning comparator, includes mixed-script duration work,
and is tagged Apache-2.0. Its official inference example is whole-result
generation, and the card does not document native streaming, fine-tuning of
this checkpoint, or timbre controls.

## Evidence matrix

| Candidate | Thai + English evidence | Local/streaming | Adaptation | Native control evidence | License evidence | Disposition |
|---|---|---|---|---|---|---|
| MOSS-TTS-Local-Transformer v1.5 | Official model card lists `th` and `en`, multilingual tags, and code-switched synthesis | Local PyTorch; official SGLang-Omni support advertises streaming and voice cloning | Official tutorials cover Local, Delay, and Realtime architectures | Language tags, voice prompt/cloning, duration and explicit pause; no documented mapping for all eight public controls | Project says all family models are Apache-2.0; re-check exact pinned weight and tokenizer artifacts | Benchmark first |
| JaiTTS-F5TTS | Official card targets Thai and discusses mixed Thai/English script; English quality is not separately established | Local CUDA/CPU selection in example; no native streaming documented | Built on F5-TTS, but checkpoint-specific training workflow is not documented on its card | Reference voice, duration predictor, and speed parameter; no native timbre controls documented | Model card and benchmark repository show Apache-2.0; card also limits intent to research/benchmarking, requiring policy review | Thai comparator |
| Typhoon2-Audio 8B | Official repository says optimized for Thai and English and shows mixed text | Local GPU required; streaming remains a TODO | No TTS adaptation workflow documented | Sampling parameters only; no stable voice/timbre-control contract | Repository is Apache-2.0; exact weight dependencies still require review | Reject: archived, heavy, no streaming |
| XTTS-v2 | Official documentation lists 16 languages but not Thai | Official streaming claim and local toolkit | GPT encoder fine-tuning documented | Voice cloning, language, and speed; no full public-control mapping | Code and weights use separate terms; model uses Coqui Public Model License | Reject: no official Thai support |

An absent feature means “not documented by the reviewed official source,” not
that implementation is impossible. Approximated DSP controls do not count as
native engine support.

## Publisher results, not reproduced

- JaiTTS-F5TTS reports RTF `0.1138`, or `0.1652` with its duration predictor.
  Its card reports Thai short CER `4.78%` (`4.26%` with duration predictor).
- The JaiTTS benchmark repository reports MOSS-TTS-v1.5 Thai short/long CER of
  `4.05%`/`4.39%`, but this is third-party evaluation by a competing candidate
  team and must not substitute for this project's held-out evaluation.
- MOSS documents an 8B llama.cpp path fitting an 8 GB GPU. That is not evidence
  that the 4B local checkpoint meets this project's latency, RAM, or VRAM gate.
- XTTS documents streaming latency below 200 ms for supported languages; Thai
  is not among those languages.

## License and provenance gate

Apache-2.0 repository or model-card metadata is evidence, not legal approval.
Before downloading a candidate, record immutable revisions and separately
verify:

1. inference/training source-code license;
2. checkpoint and tokenizer/codec licenses;
3. training/adaptation rights and derivative-weight obligations;
4. generated-output terms;
5. reference-voice and training-data consent/provenance;
6. attribution, notice, patent, trademark, and redistribution requirements.

Any conflict between a repository license, model-card metadata, embedded file,
or upstream dependency blocks use pending review. “Research prototype” wording
is treated as an additional policy restriction even when metadata says
Apache-2.0.

## Consequences

The engine adapter must initially expose only capabilities verified during the
benchmark. Unsupported public controls remain absent from `/v1/capabilities`;
they are not silently emulated. Streaming may be implemented by the selected
official backend, but first-audio latency, cancellation responsiveness, chunk
artifacts, and memory bounds remain acceptance measurements.

If MOSS misses the hard latency/memory gate, test JaiTTS-F5TTS as a bounded
sentence/chunk engine while documenting the loss of native streaming and
controls. If neither passes Thai, English, mixed-language, license, and
hardware gates, return to candidate research rather than beginning training.

## Official sources

- [MOSS-TTS official repository and model-family documentation](https://github.com/OpenMOSS/MOSS-TTS)
- [MOSS-TTS v1.5 official model card](https://github.com/OpenMOSS/MOSS-TTS/blob/main/docs/moss_tts_model_card.md)
- [JaiTTS-F5TTS official model card](https://huggingface.co/JTS-AI/JaiTTS-F5TTS)
- [JaiTTS official benchmark repository](https://github.com/JTS-AI-Team/JaiTTS)
- [Typhoon2-Audio official archived repository](https://github.com/scb-10x/typhoon2-audio)
- [XTTS-v2 official documentation](https://github.com/coqui-ai/TTS/blob/dev/docs/source/models/xtts.md)

