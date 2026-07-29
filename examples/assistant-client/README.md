# Local assistant voice provider

`local_voice_provider.py` is a reference async Python provider. It discovers
capabilities, sends sanitized speech-only text, streams PCM directly to
playback, and cancels synthesis with the same request ID during barge-in.

The provider is intentionally independent of the assistant's text/model
provider. Copy it behind your application's voice interface and keep browser or
hosted speech as separately selectable fallbacks.

