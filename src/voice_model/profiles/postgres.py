"""PostgreSQL voice-profile repository."""

import json
from collections.abc import Sequence
from datetime import datetime
from types import MappingProxyType
from typing import Any

import psycopg
from psycopg.rows import dict_row

from voice_model.profiles.models import VoiceProfile

_MIGRATION = """
CREATE TABLE IF NOT EXISTS voice_profiles (
    profile_id VARCHAR(64) PRIMARY KEY,
    display_name VARCHAR(80) NOT NULL,
    source VARCHAR(32) NOT NULL,
    language VARCHAR(16) NOT NULL,
    style VARCHAR(24) NOT NULL,
    controls JSONB NOT NULL,
    user_attested_right_to_use BOOLEAN NOT NULL CHECK (user_attested_right_to_use),
    signed_consent_record VARCHAR(160) NOT NULL,
    license_review VARCHAR(160) NOT NULL,
    reference_metadata JSONB,
    training_approved BOOLEAN NOT NULL DEFAULT FALSE,
    release_approved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS voice_profiles_updated_at_idx
    ON voice_profiles (updated_at DESC);
"""


class PostgresVoiceProfileStore:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    async def migrate(self) -> None:
        async with await psycopg.AsyncConnection.connect(self._database_url) as connection:
            await connection.execute(_MIGRATION)

    async def save(self, profile: VoiceProfile) -> VoiceProfile:
        query = """
        INSERT INTO voice_profiles (
            profile_id, display_name, source, language, style, controls,
            user_attested_right_to_use, signed_consent_record, license_review,
            reference_metadata, training_approved, release_approved, created_at, updated_at
        ) VALUES (
            %(profile_id)s, %(display_name)s, %(source)s, %(language)s, %(style)s,
            %(controls)s::jsonb, %(attested)s, %(consent)s, %(license_review)s,
            %(reference)s::jsonb, %(training)s, %(release)s, %(created_at)s, %(updated_at)s
        )
        ON CONFLICT (profile_id) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            source = EXCLUDED.source,
            language = EXCLUDED.language,
            style = EXCLUDED.style,
            controls = EXCLUDED.controls,
            user_attested_right_to_use = EXCLUDED.user_attested_right_to_use,
            signed_consent_record = EXCLUDED.signed_consent_record,
            license_review = EXCLUDED.license_review,
            reference_metadata = EXCLUDED.reference_metadata,
            training_approved = EXCLUDED.training_approved,
            release_approved = EXCLUDED.release_approved,
            updated_at = EXCLUDED.updated_at
        RETURNING *
        """
        values = {
            "profile_id": profile.profile_id,
            "display_name": profile.display_name,
            "source": profile.source,
            "language": profile.language,
            "style": profile.style,
            "controls": json.dumps(dict(profile.controls)),
            "attested": profile.user_attested_right_to_use,
            "consent": profile.signed_consent_record,
            "license_review": profile.license_review,
            "reference": json.dumps(dict(profile.reference)) if profile.reference else None,
            "training": profile.training_approved,
            "release": profile.release_approved,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }
        async with await psycopg.AsyncConnection.connect(
            self._database_url, row_factory=dict_row
        ) as connection:
            result = await connection.execute(query, values)
            row = await result.fetchone()
        if row is None:
            raise RuntimeError("PostgreSQL did not return the saved voice profile")
        return _from_row(row)

    async def list(self, *, limit: int = 100) -> Sequence[VoiceProfile]:
        async with await psycopg.AsyncConnection.connect(
            self._database_url, row_factory=dict_row
        ) as connection:
            result = await connection.execute(
                "SELECT * FROM voice_profiles ORDER BY updated_at DESC LIMIT %s", (limit,)
            )
            rows = await result.fetchall()
        return tuple(_from_row(row) for row in rows)

    async def get(self, profile_id: str) -> VoiceProfile | None:
        async with await psycopg.AsyncConnection.connect(
            self._database_url, row_factory=dict_row
        ) as connection:
            result = await connection.execute(
                "SELECT * FROM voice_profiles WHERE profile_id = %s", (profile_id,)
            )
            row = await result.fetchone()
        return _from_row(row) if row else None

    async def delete(self, profile_id: str) -> bool:
        async with await psycopg.AsyncConnection.connect(self._database_url) as connection:
            result = await connection.execute(
                "DELETE FROM voice_profiles WHERE profile_id = %s", (profile_id,)
            )
            return result.rowcount > 0

    async def close(self) -> None:
        return None


def _from_row(row: dict[str, Any]) -> VoiceProfile:
    controls = row["controls"]
    reference = row["reference_metadata"]
    if isinstance(controls, str):
        controls = json.loads(controls)
    if isinstance(reference, str):
        reference = json.loads(reference)
    return VoiceProfile(
        profile_id=row["profile_id"],
        display_name=row["display_name"],
        source=row["source"],
        language=row["language"],
        style=row["style"],
        controls=MappingProxyType({name: float(value) for name, value in controls.items()}),
        user_attested_right_to_use=row["user_attested_right_to_use"],
        signed_consent_record=row["signed_consent_record"],
        license_review=row["license_review"],
        reference=MappingProxyType(reference) if reference else None,
        training_approved=row["training_approved"],
        release_approved=row["release_approved"],
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
    )


def _datetime(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise RuntimeError("PostgreSQL returned an invalid timestamp")
    return value
