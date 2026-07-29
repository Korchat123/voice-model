"""Create or update the local PostgreSQL schema."""

import asyncio

from voice_model.profiles.postgres import PostgresVoiceProfileStore
from voice_model.service.settings import ServiceSettings


async def _migrate() -> None:
    settings = ServiceSettings.from_environment()
    if settings.database_url is None:
        raise SystemExit("VOICE_DATABASE_URL is required")
    await PostgresVoiceProfileStore(settings.database_url).migrate()


if __name__ == "__main__":
    asyncio.run(_migrate())
