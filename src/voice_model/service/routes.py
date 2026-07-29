"""Versioned HTTP routes for bounded local synthesis."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Iterator

from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from voice_model.domain import DomainError, ErrorCode, SynthesisRequest, ValidationDetail
from voice_model.engines import AudioChunk, CancellationToken, Engine
from voice_model.service.lifecycle import (
    CapacityExceededError,
    RequestConflictError,
    RequestLifecycle,
    RequestState,
)
from voice_model.service.schemas import capabilities_body, error_body
from voice_model.service.settings import ServiceSettings

_LOG = logging.getLogger(__name__)
_STATUS = {
    ErrorCode.INVALID_REQUEST: 400,
    ErrorCode.UNKNOWN_CONTROL: 400,
    ErrorCode.CONTROL_OUT_OF_RANGE: 400,
    ErrorCode.LIMIT_EXCEEDED: 400,
    ErrorCode.VOICE_NOT_FOUND: 404,
    ErrorCode.UNSUPPORTED_ENCODING: 415,
    ErrorCode.UNSUPPORTED_CAPABILITY: 422,
}


class VoiceRoutes:
    def __init__(
        self, engine: Engine, settings: ServiceSettings, lifecycle: RequestLifecycle
    ) -> None:
        self.engine = engine
        self.settings = settings
        self.lifecycle = lifecycle

    async def health(self, request: Request) -> JSONResponse:
        del request
        return JSONResponse(
            {
                "status": "ok",
                "ready": True,
                "runtime_version": "0.1.0",
                "model_loaded": True,
            }
        )

    async def capabilities(self, request: Request) -> JSONResponse:
        del request
        return JSONResponse(capabilities_body(self.engine.capabilities, self.settings))

    async def synthesis(self, request: Request) -> Response:
        request_id: str | None = None
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise DomainError(
                    ErrorCode.INVALID_REQUEST,
                    ValidationDetail("body", "must be a JSON object"),
                )
            synthesis_request = SynthesisRequest.from_mapping(
                payload, limits=self.settings.request_limits
            )
            request_id = synthesis_request.request_id
            header_id = request.headers.get("x-request-id")
            if header_id is not None and header_id != request_id:
                raise DomainError(
                    ErrorCode.INVALID_REQUEST,
                    ValidationDetail("X-Request-ID", "must equal request_id"),
                )
            predicted = self.engine.predict_duration_ms(synthesis_request)
            synthesis_request.validate_limits(
                self.settings.request_limits, predicted_audio_ms=predicted
            )
            token = await self.lifecycle.admit(request_id)
        except json.JSONDecodeError:
            return self._domain_error(
                DomainError(
                    ErrorCode.INVALID_REQUEST,
                    ValidationDetail("body", "must contain valid JSON"),
                ),
                None,
            )
        except DomainError as error:
            return self._domain_error(error, request_id)
        except RequestConflictError:
            return self._simple_error(409, "REQUEST_ID_CONFLICT", request_id, False)
        except CapacityExceededError:
            return self._simple_error(429, "CAPACITY_EXCEEDED", request_id, True)

        headers = {
            "X-Request-ID": request_id,
            "X-API-Version": "v1",
            "X-Model-ID": self.engine.capabilities.model_id,
            "X-Model-Version": self.engine.capabilities.model_version,
            "X-Runtime-Version": "0.1.0",
            "X-Audio-Encoding": "pcm_s16le",
            "X-Audio-Sample-Rate": str(synthesis_request.sample_rate_hz),
            "X-Audio-Channels": "1",
        }
        return StreamingResponse(
            self._stream(synthesis_request, token),
            media_type=f"audio/L16;rate={synthesis_request.sample_rate_hz};channels=1",
            headers=headers,
        )

    async def cancel(self, request: Request) -> Response:
        request_id = request.path_params["request_id"]
        try:
            SynthesisRequest.from_mapping(
                {
                    "request_id": request_id,
                    "text": "validation-only",
                    "language": "auto",
                    "voice": "primary",
                }
            )
        except DomainError as error:
            return self._domain_error(error, request_id)
        accepted = await self.lifecycle.cancel(request_id)
        return Response(status_code=202 if accepted else 204)

    async def _stream(
        self, synthesis_request: SynthesisRequest, cancellation: CancellationToken
    ) -> AsyncIterator[bytes]:
        active = await self.lifecycle.activate(synthesis_request.request_id)
        if not active:
            await self.lifecycle.finish(synthesis_request.request_id, RequestState.CANCELLED)
            return
        state = RequestState.COMPLETED
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.settings.request_timeout_ms / 1_000
        chunks: Iterator[AudioChunk] | None = None
        try:
            chunks = iter(self.engine.synthesize(synthesis_request, cancellation))
            while chunk := await asyncio.to_thread(_next_chunk, chunks):
                if cancellation.is_cancelled or loop.time() >= deadline:
                    cancellation.cancel()
                    state = RequestState.CANCELLED
                    break
                yield chunk.pcm_s16le
        except Exception:
            state = RequestState.FAILED
            _LOG.exception(
                "synthesis failed",
                extra={"request_id": synthesis_request.request_id},
            )
        finally:
            if chunks is not None:
                _close_iterator(chunks)
            await self.lifecycle.finish(synthesis_request.request_id, state)

    @staticmethod
    def _domain_error(error: DomainError, request_id: str | None) -> JSONResponse:
        return JSONResponse(error_body(error, request_id), status_code=_STATUS[error.code])

    @staticmethod
    def _simple_error(
        status: int, code: str, request_id: str | None, retryable: bool
    ) -> JSONResponse:
        return JSONResponse(
            {
                "error": {
                    "code": code,
                    "message": "The request could not be accepted.",
                    "request_id": request_id,
                    "details": [],
                    "retryable": retryable,
                }
            },
            status_code=status,
            headers={"Retry-After": "1"} if status == 429 else None,
        )


def _next_chunk(chunks: Iterator[AudioChunk]) -> AudioChunk | None:
    try:
        return next(chunks)
    except StopIteration:
        return None


def _close_iterator(chunks: Iterator[AudioChunk]) -> None:
    close = getattr(chunks, "close", None)
    if callable(close):
        close()
