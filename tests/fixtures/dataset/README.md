# Dataset fixtures

`manifest.example.json` is metadata for a programmatically generated test
signal. It contains no recording or cloned voice. Tests create WAV files inside
pytest temporary directories and compute their hashes at runtime.

The placeholder digest intentionally prevents this example from being accepted
as a real dataset without generating and hashing the referenced file.
