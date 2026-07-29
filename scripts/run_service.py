"""Run the loopback-only local voice service."""

import asyncio
import sys

import uvicorn

from voice_model.service import create_app
from voice_model.service.settings import ServiceSettings


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    settings = ServiceSettings.from_environment()
    uvicorn.run(
        create_app(settings=settings),
        host=settings.host,
        port=settings.port,
        access_log=False,
    )


if __name__ == "__main__":
    main()
