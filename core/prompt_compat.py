from __future__ import annotations

import json

from models.schemas import ChatMessage, ClaudeContentPart, ClaudeMessage, ContentPart


def _openai_content_to_text(content: str | list[ContentPart] | None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for part in content:
        if part.type == "text" and isinstance(part.text, str):
            parts.append(part.text)
        elif part.type == "image_url" and part.image_url is not None:
            parts.append(f"[image: {part.image_url.url}]")
    return "\n".join(parts)


def _claude_content_to_text(content: str | list[ClaudeContentPart]) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(part.text for part in content if part.type == "text" and part.text)


def openai_messages_to_prompt(messages: list[ChatMessage], tools: list[dict[str, object]] | None) -> str:
    sections: list[str] = []
    for message in messages:
        body = _openai_content_to_text(message.content)
        if not body:
            continue
        sections.append(f"{message.role}: {body}")

    if tools:
        sections.append(
            "Available tools/functions. If a tool is required, respond with a JSON object "
            "matching the requested function call schema."
        )
        sections.append(json.dumps(tools, ensure_ascii=False, indent=2))

    return "\n\n".join(sections)


def claude_messages_to_prompt(
    system: str | list[ClaudeContentPart] | None,
    messages: list[ClaudeMessage],
    tools: list[dict[str, object]] | None,
) -> str:
    sections: list[str] = []
    if isinstance(system, str) and system:
        sections.append(f"system: {system}")
    elif isinstance(system, list):
        text = _claude_content_to_text(system)
        if text:
            sections.append(f"system: {text}")

    for message in messages:
        body = _claude_content_to_text(message.content)
        if body:
            sections.append(f"{message.role}: {body}")

    if tools:
        sections.append("Available Claude tools:")
        sections.append(json.dumps(tools, ensure_ascii=False, indent=2))

    return "\n\n".join(sections)
