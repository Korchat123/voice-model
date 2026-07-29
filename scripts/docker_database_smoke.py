"""Exercise the Docker voice-profile API against real PostgreSQL."""

import json
import os
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("VOICE_MODEL_BASE_URL", "http://127.0.0.1:8765")
PROFILE_ID = "docker-smoke-voice"


def request(path: str, *, method: str = "GET", body: object | None = None) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    call = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(call, timeout=10) as response:
            payload = response.read()
            return response.status, json.loads(payload) if payload else None
    except urllib.error.HTTPError as error:
        payload = error.read()
        return error.code, json.loads(payload) if payload else None


def wait_for_service() -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/v1/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.5)
    raise RuntimeError(f"voice service did not become ready within 30 seconds: {BASE_URL}")


def main() -> None:
    wait_for_service()
    manifest = {
        "schema_version": "1.0",
        "status": "draft-user-input",
        "voice": {
            "id": PROFILE_ID,
            "display_name": "Docker Smoke Voice",
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
    status, created = request("/v1/voice-profiles", method="POST", body=manifest)
    assert status == 201, (status, created)
    assert isinstance(created, dict) and created["profile_id"] == PROFILE_ID
    status, fetched = request(f"/v1/voice-profiles/{PROFILE_ID}")
    assert status == 200 and fetched == created
    status, listing = request("/v1/voice-profiles")
    assert status == 200 and any(item["profile_id"] == PROFILE_ID for item in listing["profiles"])
    status, _ = request(f"/v1/voice-profiles/{PROFILE_ID}", method="DELETE")
    assert status == 204
    print("Docker PostgreSQL voice-profile smoke test passed")


if __name__ == "__main__":
    main()
