"""Storage protocol and deterministic in-memory implementation."""

from collections.abc import Sequence
from typing import Protocol

from voice_model.profiles.models import VoiceProfile


class VoiceProfileStore(Protocol):
    async def migrate(self) -> None: ...

    async def save(self, profile: VoiceProfile) -> VoiceProfile: ...

    async def list(self, *, limit: int = 100) -> Sequence[VoiceProfile]: ...

    async def get(self, profile_id: str) -> VoiceProfile | None: ...

    async def delete(self, profile_id: str) -> bool: ...

    async def close(self) -> None: ...


class InMemoryVoiceProfileStore:
    def __init__(self) -> None:
        self._profiles: dict[str, VoiceProfile] = {}

    async def migrate(self) -> None:
        return None

    async def save(self, profile: VoiceProfile) -> VoiceProfile:
        previous = self._profiles.get(profile.profile_id)
        if previous is not None:
            profile = VoiceProfile(
                profile_id=profile.profile_id,
                display_name=profile.display_name,
                source=profile.source,
                language=profile.language,
                style=profile.style,
                controls=profile.controls,
                user_attested_right_to_use=profile.user_attested_right_to_use,
                signed_consent_record=profile.signed_consent_record,
                license_review=profile.license_review,
                reference=profile.reference,
                training_approved=profile.training_approved,
                release_approved=profile.release_approved,
                created_at=previous.created_at,
                updated_at=profile.updated_at,
            )
        self._profiles[profile.profile_id] = profile
        return profile

    async def list(self, *, limit: int = 100) -> Sequence[VoiceProfile]:
        return tuple(
            sorted(self._profiles.values(), key=lambda item: item.updated_at, reverse=True)[:limit]
        )

    async def get(self, profile_id: str) -> VoiceProfile | None:
        return self._profiles.get(profile_id)

    async def delete(self, profile_id: str) -> bool:
        return self._profiles.pop(profile_id, None) is not None

    async def close(self) -> None:
        self._profiles.clear()
