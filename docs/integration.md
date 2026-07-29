# AI assistant integration

The local voice service is an output provider only. It must not receive
conversation state, tool calls, credentials, raw tool output, filesystem
paths, or private history. The assistant first produces and reviews a
`speechText` field, then passes only that field to the provider.

The reference client is
[`examples/assistant-client/local_voice_provider.py`](../examples/assistant-client/local_voice_provider.py).
It uses the versioned HTTP contract, performs a conservative final sanitation
check, streams PCM without buffering the complete response, and treats every
voice failure as recoverable.

## Provider flow

1. Read `/v1/capabilities` and offer only reported languages and controls.
2. Create one request ID for synthesis, playback, diagnostics, and barge-in.
3. Sanitize reviewed `speechText`; reject URLs, code fences, secret-shaped
   assignments, controls, blank text, and text beyond the advertised limit.
4. Start `/v1/synthesis` and play each PCM chunk as it arrives.
5. On mute, interruption, or new user speech, stop playback immediately and
   send `DELETE /v1/synthesis/{requestId}`.
6. If synthesis fails, keep the text assistant responsive and select an
   explicitly configured fallback provider if policy allows.

```python
from local_voice_provider import LocalVoiceProvider, VoiceControls

async with LocalVoiceProvider() as voice:
    ok = await voice.stream_to_player(
        reviewed_speech_text,
        audio_output.write,
        preset="warm",
        controls=VoiceControls(resonance=0.2, pace=-0.1),
        request_id=turn_id,
    )
    if not ok:
        diagnostics.show_text_only_mode()
```

The example records only request ID, terminal status, and exception class in
diagnostics. It never records speech text or audio. Production applications
should similarly avoid logging request payloads and must not automatically
retry incomplete audio where duplicate speech would be harmful.

## Barge-in and failure isolation

Playback cancellation and synthesis cancellation are distinct operations but
share the request ID. Stop the local audio sink first for immediate user
feedback, then call `barge_in(request_id)`. Repeating the DELETE is safe.

Failure of health discovery, connection, streaming, cancellation, or playback
must not cancel the assistant's text response or crash its event loop. The
reference `stream_to_player` method demonstrates this isolation by returning
`False`; selection of browser, hosted, or silent fallback remains an
application policy decision.

