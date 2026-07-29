"""Reference async provider for the local voice HTTP API.

This file is intentionally dependency-light and can be copied behind an
assistant application's voice-provider interface.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from dataclasses import dataclass
from uuid import uuid4

import httpx

_UNSAFE_SPEECH = re.compile(
    r"(```|https?://|www\.|(?:api[_ -]?key|password|bearer)\s*[:= ])",
    re.IGNORECASE,
)
_CONTROL_CHARACTER = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")


class VoiceServiceError(RuntimeError):
    """A recoverable provider failure that must not stop the text assistant."""


class UnsafeSpeechTextError(ValueError):
    """Text has not passed the minimum speech-only policy."""


@dataclass(frozen=True, slots=True)
class VoiceDiagnostic:
    """Privacy-safe terminal diagnostic; deliberately excludes speech text."""

    request_id: str
    status: str
    error_type: str | None = None


@dataclass(frozen=True, slots=True)
class VoiceControls:
    pitch: float | None = None
    pace: float | None = None
    energy: float | None = None
    warmth: float | None = None
    brightness: float | None = None
    breathiness: float | None = None
    resonance: float | None = None
    expressiveness: float | None = None

    def as_request(self) -> dict[str, float]:
        values = {
            name: value
            for name, value in (
                ("pitch", self.pitch),
                ("pace", self.pace),
                ("energy", self.energy),
                ("warmth", self.warmth),
                ("brightness", self.brightness),
                ("breathiness", self.breathiness),
                ("resonance", self.resonance),
                ("expressiveness", self.expressiveness),
            )
            if value is not None
        }
        if any(not -1.0 <= value <= 1.0 for value in values.values()):
            raise ValueError("voice controls must be between -1.0 and 1.0")
        return values


def sanitize_speech_text(value: str, *, maximum_characters: int = 2_000) -> str:
    """Normalize speech-only text and reject likely code, URLs, or secrets."""

    if not isinstance(value, str):
        raise UnsafeSpeechTextError("speech text must be a string")
    normalized = unicodedata.normalize("NFC", value)
    normalized = _CONTROL_CHARACTER.sub("", normalized)
    normalized = " ".join(normalized.split())
    if not normalized:
        raise UnsafeSpeechTextError("speech text must not be blank")
    if len(normalized) > maximum_characters:
        raise UnsafeSpeechTextError("speech text exceeds the advertised limit")
    if _UNSAFE_SPEECH.search(normalized):
        raise UnsafeSpeechTextError("speech text contains disallowed content")
    return normalized


class LocalVoiceProvider:
    """Async streaming provider with cancellation and failure isolation."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=15.0)
        self._active_request_id: str | None = None
        self.last_diagnostic: VoiceDiagnostic | None = None

    async def __aenter__(self) -> LocalVoiceProvider:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def capabilities(self) -> Mapping[str, object]:
        try:
            response = await self._client.get("/v1/capabilities")
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise VoiceServiceError("voice capabilities are unavailable") from error
        if not isinstance(payload, dict):
            raise VoiceServiceError("voice capabilities are malformed")
        return payload

    async def stream(
        self,
        speech_text: str,
        *,
        language: str = "auto",
        voice: str = "primary",
        preset: str = "neutral",
        controls: VoiceControls | None = None,
        request_id: str | None = None,
    ) -> AsyncIterator[bytes]:
        """Yield PCM chunks. Callers own playback and should invoke barge_in."""

        resolved_id = request_id or f"assistant-{uuid4().hex}"
        if not _REQUEST_ID.fullmatch(resolved_id):
            raise ValueError("request_id has an invalid format")
        safe_text = sanitize_speech_text(speech_text)
        payload: dict[str, object] = {
            "request_id": resolved_id,
            "text": safe_text,
            "language": language,
            "voice": voice,
            "preset": preset,
            "encoding": "pcm_s16le",
            "return_timings": False,
        }
        if controls is not None:
            payload["controls"] = controls.as_request()
        self._active_request_id = resolved_id
        try:
            async with self._client.stream(
                "POST",
                "/v1/synthesis",
                headers={"X-Request-ID": resolved_id},
                json=payload,
            ) as response:
                if response.status_code != 200:
                    raise VoiceServiceError(f"voice synthesis failed ({response.status_code})")
                if response.headers.get("x-request-id") != resolved_id:
                    raise VoiceServiceError("voice service returned a mismatched request ID")
                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk
            self.last_diagnostic = VoiceDiagnostic(resolved_id, "completed")
        except httpx.HTTPError as error:
            self.last_diagnostic = VoiceDiagnostic(resolved_id, "failed", type(error).__name__)
            raise VoiceServiceError("voice streaming is unavailable") from error
        except VoiceServiceError as error:
            self.last_diagnostic = VoiceDiagnostic(resolved_id, "failed", type(error).__name__)
            raise
        finally:
            if self._active_request_id == resolved_id:
                self._active_request_id = None

    async def barge_in(self, request_id: str | None = None) -> bool:
        """Cancel synthesis using the playback request ID; safe to repeat."""

        resolved_id = request_id or self._active_request_id
        if resolved_id is None:
            return False
        if not _REQUEST_ID.fullmatch(resolved_id):
            raise ValueError("request_id has an invalid format")
        try:
            response = await self._client.delete(f"/v1/synthesis/{resolved_id}")
            return response.status_code in {202, 204}
        except httpx.HTTPError:
            return False

    async def stream_to_player(
        self,
        speech_text: str,
        play_chunk: Callable[[bytes], Awaitable[None]],
        *,
        language: str = "auto",
        voice: str = "primary",
        preset: str = "neutral",
        controls: VoiceControls | None = None,
        request_id: str | None = None,
    ) -> bool:
        """Failure-isolation boundary: return false while text UI continues."""

        try:
            async for chunk in self.stream(
                speech_text,
                language=language,
                voice=voice,
                preset=preset,
                controls=controls,
                request_id=request_id,
            ):
                await play_chunk(chunk)
        except (VoiceServiceError, UnsafeSpeechTextError, ValueError):
            return False
        return True
