"""Bounded HTTP routes for voice-profile metadata."""

import json
import re

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from voice_model.profiles import VoiceProfile, VoiceProfileStore

_PROFILE_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
_MAX_BODY_BYTES = 64 * 1024


class VoiceProfileRoutes:
    def __init__(self, store: VoiceProfileStore) -> None:
        self.store = store

    async def save(self, request: Request) -> JSONResponse:
        length = request.headers.get("content-length")
        if length is not None:
            try:
                if int(length) > _MAX_BODY_BYTES:
                    return _error(413, "PROFILE_TOO_LARGE", "Profile metadata is too large.")
            except ValueError:
                return _error(400, "INVALID_PROFILE", "Content-Length must be an integer.")
        try:
            body = await request.body()
            if len(body) > _MAX_BODY_BYTES:
                return _error(413, "PROFILE_TOO_LARGE", "Profile metadata is too large.")
            profile = VoiceProfile.from_setup_manifest(json.loads(body))
            saved = await self.store.save(profile)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
            return _error(400, "INVALID_PROFILE", str(error))
        except Exception:
            return _error(503, "PROFILE_STORE_UNAVAILABLE", "Local profile storage is unavailable.")
        return JSONResponse(saved.to_dict(), status_code=201)

    async def list(self, request: Request) -> JSONResponse:
        del request
        try:
            profiles = await self.store.list(limit=100)
        except Exception:
            return _error(503, "PROFILE_STORE_UNAVAILABLE", "Local profile storage is unavailable.")
        return JSONResponse({"profiles": [profile.to_dict() for profile in profiles]})

    async def get(self, request: Request) -> JSONResponse:
        profile_id = request.path_params["profile_id"]
        if not _PROFILE_ID.fullmatch(profile_id):
            return _error(400, "INVALID_PROFILE_ID", "Profile ID is invalid.")
        try:
            profile = await self.store.get(profile_id)
        except Exception:
            return _error(503, "PROFILE_STORE_UNAVAILABLE", "Local profile storage is unavailable.")
        if profile is None:
            return _error(404, "PROFILE_NOT_FOUND", "Voice profile was not found.")
        return JSONResponse(profile.to_dict())

    async def delete(self, request: Request) -> Response:
        profile_id = request.path_params["profile_id"]
        if not _PROFILE_ID.fullmatch(profile_id):
            return _error(400, "INVALID_PROFILE_ID", "Profile ID is invalid.")
        try:
            deleted = await self.store.delete(profile_id)
        except Exception:
            return _error(503, "PROFILE_STORE_UNAVAILABLE", "Local profile storage is unavailable.")
        return Response(status_code=204 if deleted else 404)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "message": message, "retryable": status == 503}},
        status_code=status,
    )
