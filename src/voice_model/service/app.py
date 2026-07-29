"""ASGI application factory."""

from starlette.applications import Starlette
from starlette.routing import Route

from voice_model.engines import Engine
from voice_model.engines.adapters import CapabilityCheckedEngine
from voice_model.engines.fake import FakeEngine
from voice_model.service.lifecycle import RequestLifecycle
from voice_model.service.routes import VoiceRoutes
from voice_model.service.settings import ServiceSettings


def create_app(
    *, engine: Engine | None = None, settings: ServiceSettings | None = None
) -> Starlette:
    resolved_settings = settings or ServiceSettings()
    resolved_engine = CapabilityCheckedEngine(engine or FakeEngine())
    lifecycle = RequestLifecycle(
        resolved_settings.max_concurrent_requests,
        resolved_settings.max_queued_requests,
        resolved_settings.tombstone_limit,
    )
    handlers = VoiceRoutes(resolved_engine, resolved_settings, lifecycle)
    app = Starlette(
        debug=False,
        routes=[
            Route("/v1/health", handlers.health, methods=["GET"]),
            Route("/v1/capabilities", handlers.capabilities, methods=["GET"]),
            Route("/v1/synthesis", handlers.synthesis, methods=["POST"]),
            Route("/v1/synthesis/{request_id}", handlers.cancel, methods=["DELETE"]),
        ],
    )
    app.state.settings = resolved_settings
    return app
