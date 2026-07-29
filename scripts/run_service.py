"""Run the loopback-only local voice service."""

import uvicorn

from voice_model.service import create_app
from voice_model.service.settings import ServiceSettings


def main() -> None:
    settings = ServiceSettings.from_environment()
    uvicorn.run(
        create_app(settings=settings),
        host=settings.host,
        port=settings.port,
        access_log=False,
    )


if __name__ == "__main__":
    main()
