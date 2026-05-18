from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator


def sse_event(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def done_event() -> str:
    return "data: [DONE]\n\n"


async def openai_stream_events(
    text_stream: AsyncIterator[str],
    model: str,
    response_id: str,
) -> AsyncIterator[str]:
    previous = ""
    created = int(time.time())
    async for text in text_stream:
        delta = _delta(previous, text)
        previous = text
        if not delta:
            continue
        yield sse_event(
            {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {"content": delta}, "finish_reason": None}],
            }
        )
    yield sse_event(
        {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
    )
    yield done_event()


async def claude_stream_events(text_stream: AsyncIterator[str], message_id: str) -> AsyncIterator[str]:
    previous = ""
    yield sse_event({"type": "message_start", "message": {"id": message_id, "type": "message", "role": "assistant"}})
    yield sse_event({"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}})
    async for text in text_stream:
        delta = _delta(previous, text)
        previous = text
        if delta:
            yield sse_event({"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": delta}})
    yield sse_event({"type": "content_block_stop", "index": 0})
    yield sse_event({"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None}})
    yield sse_event({"type": "message_stop"})


def _delta(previous: str, current: str) -> str:
    if current.startswith(previous):
        return current[len(previous) :]
    return current
