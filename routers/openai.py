from __future__ import annotations

import secrets
import time
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import Settings
from app.dependencies import get_file_store, get_gemini_manager, get_settings
from core.gemini_client import GeminiClientManager
from core.history import FileStore
from core.prompt_compat import openai_messages_to_prompt
from core.stream_adapter import openai_stream_events
from core.tool_adapter import extract_tool_calls
from models.schemas import (
    FileUploadResponse,
    ModelCard,
    ModelsResponse,
    OpenAIChatCompletionRequest,
)

router = APIRouter(prefix="/v1", tags=["openai"])


@router.get("/models", response_model=ModelsResponse)
async def list_models(settings: Settings = Depends(get_settings)) -> ModelsResponse:
    return ModelsResponse(data=[ModelCard(id=model) for model in settings.models])


@router.post("/files", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    purpose: str = Form("assistants"),
    store: FileStore = Depends(get_file_store),
) -> FileUploadResponse:
    record = await store.save(file, purpose)
    return FileUploadResponse(id=record.id, filename=record.filename, bytes=record.bytes, purpose=record.purpose)


@router.get("/files")
async def list_files(store: FileStore = Depends(get_file_store)) -> dict[str, object]:
    return {
        "object": "list",
        "data": [
            {
                "id": record.id,
                "object": "file",
                "bytes": record.bytes,
                "filename": record.filename,
                "purpose": record.purpose,
            }
            for record in store.list_files()
        ],
    }


@router.delete("/files/{file_id}")
async def delete_file(file_id: str, store: FileStore = Depends(get_file_store)) -> dict[str, object]:
    deleted = store.delete(file_id)
    return {"id": file_id, "object": "file", "deleted": deleted}


@router.post("/chat/completions", response_model=None)
async def create_chat_completion(
    request: OpenAIChatCompletionRequest,
    manager: GeminiClientManager = Depends(get_gemini_manager),
    store: FileStore = Depends(get_file_store),
) -> JSONResponse | StreamingResponse:
    prompt = openai_messages_to_prompt(request.messages, request.tools)
    files = store.get_paths(request.file_ids)
    response_id = f"chatcmpl-{secrets.token_hex(12)}"

    if request.stream:
        return StreamingResponse(
            openai_stream_events(_stream_text(manager, prompt, request.model, files, request.temporary), request.model, response_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        text = await manager.generate(prompt, request.model, files, request.temporary)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    created = int(time.time())
    tool_calls = extract_tool_calls(text) if request.tools else []
    message: dict[str, object] = {"role": "assistant", "content": text if not tool_calls else None}
    finish_reason = "stop"
    if tool_calls:
        message["tool_calls"] = tool_calls
        finish_reason = "tool_calls"

    return JSONResponse(
        {
            "id": response_id,
            "object": "chat.completion",
            "created": created,
            "model": request.model,
            "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
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
    prompt_tokens = max(len(prompt) // 4, 1) if prompt else 0
    completion_tokens = max(len(completion) // 4, 1) if completion else 0
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }
