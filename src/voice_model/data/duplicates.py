"""Exact duplicate and cross-split prompt leakage detection."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

from voice_model.data.manifest import ClipRecord


def normalize_transcript(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text).casefold()
    return re.sub(r"\W+", "", normalized, flags=re.UNICODE)


def duplicate_audio_groups(clips: tuple[ClipRecord, ...]) -> list[tuple[str, ...]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for clip in clips:
        groups[clip.audio_sha256].append(clip.clip_id)
    return [tuple(ids) for ids in groups.values() if len(ids) > 1]


def leakage_errors(
    clips: tuple[ClipRecord, ...],
    *,
    similarity_threshold: float = 0.94,
) -> list[str]:
    """Find exact, family, and near-transcript leakage across assigned splits."""
    errors: set[str] = set()
    assigned = [clip for clip in clips if clip.split is not None]
    for index, left in enumerate(assigned):
        left_text = normalize_transcript(left.transcript)
        for right in assigned[index + 1 :]:
            if left.split == right.split:
                continue
            pair = " / ".join(sorted((left.clip_id, right.clip_id)))
            right_text = normalize_transcript(right.transcript)
            if left.prompt_family_id == right.prompt_family_id:
                errors.add(f"prompt family crosses splits: {pair}")
            if left_text == right_text:
                errors.add(f"exact transcript crosses splits: {pair}")
            elif left_text and right_text:
                score = SequenceMatcher(None, left_text, right_text).ratio()
                if score >= similarity_threshold:
                    errors.add(f"near transcript crosses splits ({score:.3f}): {pair}")
    return sorted(errors)
