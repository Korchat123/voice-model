"""Synthesis completion metadata."""

from dataclasses import dataclass

from voice_model.domain.controls import VoiceControls


@dataclass(frozen=True, slots=True)
class SynthesisMetadata:
    """Validated terminal metadata emitted separately from audio bytes."""

    request_id: str
    model_id: str
    model_version: str
    runtime_version: str
    sample_rate_hz: int
    duration_ms: int
    applied_controls: VoiceControls
    completed: bool
    cancelled: bool = False

    def __post_init__(self) -> None:
        identifiers = (self.request_id, self.model_id, self.model_version, self.runtime_version)
        if any(not isinstance(value, str) or not value for value in identifiers):
            raise ValueError("metadata identifiers must be non-empty strings")
        audio_values = (self.sample_rate_hz, self.duration_ms)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in audio_values):
            raise ValueError("metadata audio values must be integers")
        if self.sample_rate_hz < 1 or self.duration_ms < 0:
            raise ValueError("metadata audio values must be non-negative")
        if not isinstance(self.applied_controls, VoiceControls):
            raise ValueError("metadata controls must be resolved")
        if not isinstance(self.completed, bool) or not isinstance(self.cancelled, bool):
            raise ValueError("metadata terminal flags must be booleans")
        if self.completed and self.cancelled:
            raise ValueError("completed synthesis cannot also be cancelled")
