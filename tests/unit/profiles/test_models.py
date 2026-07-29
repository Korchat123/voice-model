from __future__ import annotations

import pytest

from voice_model.profiles.models import VoiceProfile


def manifest(**voice_updates: object) -> dict[str, object]:
    voice: dict[str, object] = {
        "id": "test-voice",
        "display_name": "Test Voice",
        "source": "licensed-synthetic",
        "language": "mixed",
        "style": "neutral",
        "controls": {"pitch": 0.0, "resonance": -0.2},
    }
    voice.update(voice_updates)
    return {
        "schema_version": "1.0",
        "voice": voice,
        "authorization": {
            "user_attested_right_to_use": True,
            "signed_consent_record": "USER_INPUT_REQUIRED",
            "license_review": "USER_INPUT_REQUIRED",
        },
        "reference": None,
        "safety": {"training_approved": False, "release_approved": False},
    }


def test_profile_accepts_bounded_metadata_without_audio() -> None:
    profile = VoiceProfile.from_setup_manifest(manifest())
    assert profile.profile_id == "test-voice"
    assert profile.controls["resonance"] == -0.2
    assert profile.reference is None
    assert not profile.training_approved


@pytest.mark.parametrize(
    "updates",
    [
        {"id": "../private"},
        {"source": "celebrity-scrape"},
        {"controls": {"pitch": float("nan")}},
        {"controls": {"unknown": 0.0}},
    ],
)
def test_profile_rejects_unsafe_voice_metadata(updates: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        VoiceProfile.from_setup_manifest(manifest(**updates))


def test_profile_rejects_file_paths_and_invalid_reference_hashes() -> None:
    payload = manifest()
    payload["reference"] = {
        "filename": "../private.wav",
        "media_type": "audio/wav",
        "byte_size": 10,
        "sha256": "0" * 64,
    }
    with pytest.raises(ValueError, match="basename"):
        VoiceProfile.from_setup_manifest(payload)


def test_profile_requires_right_to_use_attestation() -> None:
    payload = manifest()
    payload["authorization"] = {
        "user_attested_right_to_use": False,
        "signed_consent_record": "USER_INPUT_REQUIRED",
        "license_review": "USER_INPUT_REQUIRED",
    }
    with pytest.raises(ValueError, match="attestation"):
        VoiceProfile.from_setup_manifest(payload)
