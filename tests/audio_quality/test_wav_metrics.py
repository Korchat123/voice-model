import wave
from pathlib import Path

import pytest

from voice_model.evaluation import intelligibility_proxy, measure_wav


def _write_wav(path: Path, samples: list[int], *, sample_rate: int = 24_000) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(
            b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples)
        )


def test_pcm_metrics_are_measured_from_samples(tmp_path: Path) -> None:
    path = tmp_path / "fixture.wav"
    _write_wav(path, [0, 1000, -1000, 32767])

    metrics = measure_wav(path)

    assert metrics.frames == 4
    assert metrics.duration_ms == pytest.approx(4 / 24)
    assert metrics.peak_dbfs == pytest.approx(0.0)
    assert metrics.clipped_samples == 1
    assert metrics.silence_ratio == 0.25


def test_empty_wav_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "empty.wav"
    _write_wav(path, [])

    with pytest.raises(ValueError, match="no audio"):
        measure_wav(path)


def test_intelligibility_proxy_is_labeled_sanity_measure(tmp_path: Path) -> None:
    path = tmp_path / "proxy.wav"
    _write_wav(path, [1000] * 24_000)

    proxy = intelligibility_proxy("ab cd", measure_wav(path))

    assert proxy.normalized_character_count == 4
    assert proxy.characters_per_second == 4.0
    assert proxy.voiced_ms_per_character == 250.0
