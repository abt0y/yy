from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ImageUrl(BaseModel):
    url: str
    detail: str | None = None


class ContentPart(BaseModel):
    type: str
    text: str | None = None
    image_url: ImageUrl | None = None


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool", "developer"] | str
    content: str | list[ContentPart] | None = None
    name: str | None = None
    tool_call_id: str | None = None


class OpenAIChatCompletionRequest(BaseModel):
    model: str = "gemini-2.5-pro"
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    tools: list[dict[str, object]] | None = None
    tool_choice: str | dict[str, object] | None = None
    file_ids: list[str] = Field(default_factory=list)
    temporary: bool | None = None


class ClaudeContentPart(BaseModel):
    type: str
    text: str | None = None


class ClaudeMessage(BaseModel):
    role: Literal["user", "assistant"] | str
    content: str | list[ClaudeContentPart]


class ClaudeMessagesRequest(BaseModel):
    model: str = "gemini-2.5-pro"
    max_tokens: int = 1024
    messages: list[ClaudeMessage]
    system: str | list[ClaudeContentPart] | None = None
    stream: bool = False
    tools: list[dict[str, object]] | None = None
    file_ids: list[str] = Field(default_factory=list)
    temporary: bool | None = None


class GeminiNativeRequest(BaseModel):
    model: str = "gemini-2.5-pro"
    prompt: str
    stream: bool = False
    files: list[str] = Field(default_factory=list)
    temporary: bool | None = None


class CookieAddRequest(BaseModel):
    id: str | None = None
    secure_1psid: str
    secure_1psidts: str = ""
    proxy: str | None = None
    enabled: bool = True


class CookieRecord(BaseModel):
    id: str
    enabled: bool
    fail_count: int
    proxy: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    accounts: int
    enabled_accounts: int


class FileUploadResponse(BaseModel):
    id: str
    filename: str
    bytes: int
    purpose: str


class ModelCard(BaseModel):
    id: str
    object: Literal["model"] = "model"
    owned_by: str = "gemini-web-api"


class ModelsResponse(BaseModel):
    object: Literal["list"] = "list"
    data: list[ModelCard]
