"""Controllable local voice synthesis."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("voice-model")
except PackageNotFoundError:  # pragma: no cover - source-tree fallback
    __version__ = "0.0.0+uninstalled"

__all__ = ["__version__"]
