from __future__ import annotations

import json
import re


def extract_tool_calls(text: str) -> list[dict[str, object]]:
    stripped = text.strip()
    if not stripped:
        return []

    candidates = [stripped]
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL | re.IGNORECASE)
    candidates.extend(item.strip() for item in fenced)

    for candidate in candidates:
        parsed = _parse_json_object(candidate)
        if parsed is None:
            continue
        tool_calls = _tool_calls_from_json(parsed)
        if tool_calls:
            return tool_calls
    return []


def _parse_json_object(value: str) -> dict[str, object] | None:
    try:
        parsed: object = json.loads(value)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _tool_calls_from_json(parsed: dict[str, object]) -> list[dict[str, object]]:
    direct = parsed.get("tool_calls")
    if isinstance(direct, list):
        calls = [item for item in direct if isinstance(item, dict)]
        return [dict(item) for item in calls]

    name = parsed.get("name") or parsed.get("function")
    arguments = parsed.get("arguments") or parsed.get("args") or {}
    if isinstance(name, str) and name:
        argument_text = arguments if isinstance(arguments, str) else json.dumps(arguments, ensure_ascii=False)
        return [
            {
                "id": "call_0",
                "type": "function",
                "function": {"name": name, "arguments": argument_text},
            }
        ]
    return []
