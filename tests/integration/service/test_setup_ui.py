from __future__ import annotations

from starlette.testclient import TestClient

from voice_model.service import create_app


def test_setup_ui_is_available_from_root() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/setup"

        page = client.get("/setup")
        assert page.status_code == 200
        assert "Voice Workshop" in page.text
        assert "My consented recording" in page.text
        assert "Pinched" in page.text


def test_setup_assets_have_strict_browser_security_headers() -> None:
    with TestClient(create_app()) as client:
        for path, content_type in (
            ("/setup", "text/html"),
            ("/setup/app.css", "text/css"),
            ("/setup/app.js", "text/javascript"),
        ):
            response = client.get(path)
            assert response.status_code == 200
            assert content_type in response.headers["content-type"]
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["x-frame-options"] == "DENY"
            assert "connect-src 'self'" in response.headers["content-security-policy"]


def test_setup_javascript_keeps_recordings_in_browser() -> None:
    with TestClient(create_app()) as client:
        script = client.get("/setup/app.js").text
    assert "recordings_uploaded_by_ui: false" in script
    assert "crypto.subtle.digest" in script
    assert "URL.createObjectURL" in script
    assert 'fetch("/v1/synthesis"' in script
