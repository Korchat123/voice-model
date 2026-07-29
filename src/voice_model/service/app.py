"""ASGI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.routing import Route

from voice_model.engines import Engine
from voice_model.engines.adapters import CapabilityCheckedEngine
from voice_model.engines.fake import FakeEngine
from voice_model.profiles import InMemoryVoiceProfileStore, VoiceProfileStore
from voice_model.profiles.postgres import PostgresVoiceProfileStore
from voice_model.service.lifecycle import RequestLifecycle
from voice_model.service.profile_routes import VoiceProfileRoutes
from voice_model.service.routes import VoiceRoutes
from voice_model.service.settings import ServiceSettings
from voice_model.service.setup_ui import root_redirect, setup_page, setup_script, setup_styles


def create_app(
    *,
    engine: Engine | None = None,
    settings: ServiceSettings | None = None,
    profile_store: VoiceProfileStore | None = None,
) -> Starlette:
    resolved_settings = settings or ServiceSettings()
    resolved_engine = CapabilityCheckedEngine(engine or FakeEngine())
    resolved_store = profile_store or (
        PostgresVoiceProfileStore(resolved_settings.database_url)
        if resolved_settings.database_url
        else InMemoryVoiceProfileStore()
    )
    lifecycle = RequestLifecycle(
        resolved_settings.max_concurrent_requests,
        resolved_settings.max_queued_requests,
        resolved_settings.tombstone_limit,
    )
    handlers = VoiceRoutes(resolved_engine, resolved_settings, lifecycle)
    profile_handlers = VoiceProfileRoutes(resolved_store)

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        del app
        await resolved_store.migrate()
        try:
            yield
        finally:
            await resolved_store.close()

    app = Starlette(
        debug=False,
        lifespan=lifespan,
        routes=[
            Route("/", root_redirect, methods=["GET"]),
            Route("/setup", setup_page, methods=["GET"]),
            Route("/setup/app.css", setup_styles, methods=["GET"]),
            Route("/setup/app.js", setup_script, methods=["GET"]),
            Route("/v1/health", handlers.health, methods=["GET"]),
            Route("/v1/capabilities", handlers.capabilities, methods=["GET"]),
            Route("/v1/synthesis", handlers.synthesis, methods=["POST"]),
            Route("/v1/synthesis/{request_id}", handlers.cancel, methods=["DELETE"]),
            Route("/v1/voice-profiles", profile_handlers.save, methods=["POST"]),
            Route("/v1/voice-profiles", profile_handlers.list, methods=["GET"]),
            Route("/v1/voice-profiles/{profile_id}", profile_handlers.get, methods=["GET"]),
            Route("/v1/voice-profiles/{profile_id}", profile_handlers.delete, methods=["DELETE"]),
        ],
    )
    app.state.settings = resolved_settings
    app.state.profile_store = resolved_store
    return app
