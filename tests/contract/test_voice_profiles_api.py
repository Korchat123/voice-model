from __future__ import annotations

from starlette.testclient import TestClient

from voice_model.service import create_app


def manifest() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "status": "draft-user-input",
        "voice": {
            "id": "api-test-voice",
            "display_name": "API Test Voice",
            "source": "licensed-synthetic",
            "language": "mixed",
            "style": "neutral",
            "controls": {"pitch": 0.0, "resonance": 0.0},
        },
        "authorization": {
            "user_attested_right_to_use": True,
            "signed_consent_record": "USER_INPUT_REQUIRED",
            "license_review": "USER_INPUT_REQUIRED",
        },
        "reference": None,
        "safety": {"training_approved": False, "release_approved": False},
    }


def test_voice_profile_round_trip_uses_metadata_only() -> None:
    with TestClient(create_app()) as client:
        created = client.post("/v1/voice-profiles", json=manifest())
        assert created.status_code == 201
        assert created.json()["profile_id"] == "api-test-voice"
        assert created.json()["reference"] is None

        fetched = client.get("/v1/voice-profiles/api-test-voice")
        assert fetched.status_code == 200
        assert fetched.json() == created.json()

        listing = client.get("/v1/voice-profiles")
        assert listing.status_code == 200
        assert listing.json()["profiles"] == [created.json()]

        deleted = client.delete("/v1/voice-profiles/api-test-voice")
        assert deleted.status_code == 204
        assert client.get("/v1/voice-profiles/api-test-voice").status_code == 404


def test_voice_profile_api_rejects_missing_consent_and_oversized_metadata() -> None:
    payload = manifest()
    payload["authorization"] = {"user_attested_right_to_use": False}
    with TestClient(create_app()) as client:
        denied = client.post("/v1/voice-profiles", json=payload)
        assert denied.status_code == 400
        assert denied.json()["error"]["code"] == "INVALID_PROFILE"

        oversized = client.post(
            "/v1/voice-profiles",
            content=b"{}",
            headers={"content-type": "application/json", "content-length": "65537"},
        )
        assert oversized.status_code == 413
