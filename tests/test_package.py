"""Package-level smoke tests."""

from voice_model import __version__


def test_package_exposes_a_version() -> None:
    """Installed package metadata is available to diagnostics."""
    assert __version__
