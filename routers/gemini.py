from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import Settings
from app.dependencies import get_file_store, get_gemini_manager, get_settings
from core.gemini_client import GeminiClientManager
from core.history import FileStore
from core.stream_adapter import sse_event, done_event
from models.schemas import GeminiNativeRequest, ModelCard, ModelsResponse

router = APIRouter(tags=["gemini"])


@router.get("/v1beta/models", response_model=ModelsResponse)
async def list_native_models(settings: Settings = Depends(get_settings)) -> ModelsResponse:
    return ModelsResponse(data=[ModelCard(id=model) for model in settings.models])


@router.post("/gemini/generate", response_model=None)
async def generate_native(
    request: GeminiNativeRequest,
    manager: GeminiClientManager = Depends(get_gemini_manager),
    store: FileStore = Depends(get_file_store),
) -> JSONResponse | StreamingResponse:
    files = store.get_paths(request.files)
    if request.stream:
        return StreamingResponse(
            _native_stream(manager, request.prompt, request.model, files, request.temporary),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    try:
        text = await manager.generate(request.prompt, request.model, files, request.temporary)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return JSONResponse({"model": request.model, "text": text})


async def _native_stream(
    manager: GeminiClientManager,
    prompt: str,
    model: str,
    files: list[Path],
    temporary: bool | None,
) -> AsyncIterator[str]:
    try:
        async for text in manager.stream(prompt, model, files, temporary):
            yield sse_event({"text": text})
        yield done_event()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
