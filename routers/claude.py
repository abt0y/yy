from __future__ import annotations

import secrets
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.dependencies import get_file_store, get_gemini_manager
from core.gemini_client import GeminiClientManager
from core.history import FileStore
from core.prompt_compat import claude_messages_to_prompt
from core.stream_adapter import claude_stream_events
from core.tool_adapter import extract_tool_calls
from models.schemas import ClaudeMessagesRequest

router = APIRouter(tags=["claude"])


@router.post("/v1/messages", response_model=None)
@router.post("/anthropic/v1/messages", response_model=None)
async def create_message(
    request: ClaudeMessagesRequest,
    manager: GeminiClientManager = Depends(get_gemini_manager),
    store: FileStore = Depends(get_file_store),
) -> JSONResponse | StreamingResponse:
    prompt = claude_messages_to_prompt(request.system, request.messages, request.tools)
    files = store.get_paths(request.file_ids)
    message_id = f"msg_{secrets.token_hex(12)}"

    if request.stream:
        return StreamingResponse(
            claude_stream_events(_stream_text(manager, prompt, request.model, files, request.temporary), message_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        text = await manager.generate(prompt, request.model, files, request.temporary)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    tool_calls = extract_tool_calls(text) if request.tools else []
    content: list[dict[str, object]] = []
    if tool_calls:
        for index, tool_call in enumerate(tool_calls):
            function = tool_call.get("function")
            if isinstance(function, dict):
                name = function.get("name")
                arguments = function.get("arguments")
                content.append(
                    {
                        "type": "tool_use",
                        "id": str(tool_call.get("id") or f"toolu_{index}"),
                        "name": name if isinstance(name, str) else "tool",
                        "input": arguments if isinstance(arguments, dict) else {"arguments": str(arguments)},
                    }
                )
    else:
        content.append({"type": "text", "text": text})

    return JSONResponse(
        {
            "id": message_id,
            "type": "message",
            "role": "assistant",
            "model": request.model,
            "content": content,
            "stop_reason": "tool_use" if tool_calls else "end_turn",
            "stop_sequence": None,
            "usage": _usage(prompt, text),
        }
    )


async def _stream_text(
    manager: GeminiClientManager,
    prompt: str,
    model: str,
    files: list[Path],
    temporary: bool | None,
) -> AsyncIterator[str]:
    try:
        async for text in manager.stream(prompt, model, files, temporary):
            yield text
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


def _usage(prompt: str, completion: str) -> dict[str, int]:
    input_tokens = max(len(prompt) // 4, 1) if prompt else 0
    output_tokens = max(len(completion) // 4, 1) if completion else 0
    return {"input_tokens": input_tokens, "output_tokens": output_tokens}
