"""Fixed routes for the local voice setup interface."""

from pathlib import Path

from starlette.requests import Request
from starlette.responses import FileResponse, RedirectResponse, Response

_ASSET_ROOT = Path(__file__).parent.parent / "ui"
_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "media-src 'self' blob:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'none'; "
        "frame-ancestors 'none'; "
        "form-action 'self'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


async def root_redirect(request: Request) -> RedirectResponse:
    del request
    return RedirectResponse("/setup", status_code=307)


async def setup_page(request: Request) -> Response:
    del request
    return _asset_response("index.html", "text/html; charset=utf-8")


async def setup_styles(request: Request) -> Response:
    del request
    return _asset_response("app.css", "text/css; charset=utf-8")


async def setup_script(request: Request) -> Response:
    del request
    return _asset_response("app.js", "text/javascript; charset=utf-8")


def _asset_response(name: str, media_type: str) -> FileResponse:
    return FileResponse(_ASSET_ROOT / name, media_type=media_type, headers=_SECURITY_HEADERS)
