from __future__ import annotations

import asyncio
import os
import sys

import pytest

from voice_model.profiles.models import VoiceProfile
from voice_model.profiles.postgres import PostgresVoiceProfileStore

pytestmark = pytest.mark.database


def manifest(profile_id: str) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "status": "draft-user-input",
        "voice": {
            "id": profile_id,
            "display_name": "Database Integration Voice",
            "source": "licensed-synthetic",
            "language": "mixed",
            "style": "neutral",
            "controls": {"pitch": 0.0, "resonance": -0.2},
        },
        "authorization": {
            "user_attested_right_to_use": True,
            "signed_consent_record": "USER_INPUT_REQUIRED",
            "license_review": "USER_INPUT_REQUIRED",
        },
        "reference": None,
        "safety": {"training_approved": False, "release_approved": False},
    }


def test_real_postgres_profile_round_trip() -> None:
    database_url = os.environ.get("VOICE_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("VOICE_TEST_DATABASE_URL is not configured")

    async def check() -> None:
        store = PostgresVoiceProfileStore(database_url)
        await store.migrate()
        profile = VoiceProfile.from_setup_manifest(manifest("postgres-integration"))
        saved = await store.save(profile)
        assert await store.get(saved.profile_id) == saved
        assert saved in await store.list()
        assert await store.delete(saved.profile_id)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check())
