"""Minimal Claude Messages API HTTP helper (no external SDK dependency)."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ClaudeApiHttpError(RuntimeError):
    """Raised when Claude API HTTP call fails."""


def request_claude_message(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    data = json.dumps(body, ensure_ascii=True).encode("utf-8")
    req = Request(
        url="https://api.anthropic.com/v1/messages",
        data=data,
        method="POST",
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )

    try:
        with urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:
            detail = ""
        if detail:
            raise ClaudeApiHttpError(f"claude API HTTP {exc.code}: {detail}") from exc
        raise ClaudeApiHttpError(f"claude API HTTP {exc.code}") from exc
    except URLError as exc:
        reason = exc.reason if getattr(exc, "reason", None) else str(exc)
        raise ClaudeApiHttpError(f"claude API connection error: {reason}") from exc
    except Exception as exc:
        raise ClaudeApiHttpError("claude API request failed") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ClaudeApiHttpError("claude API returned non-JSON response") from exc

    if not isinstance(payload, dict):
        raise ClaudeApiHttpError("claude API response must be an object")

    if "error" in payload and isinstance(payload.get("error"), dict):
        err = payload["error"]
        message = str(err.get("message") or "unknown error")
        err_type = str(err.get("type") or "error")
        raise ClaudeApiHttpError(f"claude API error ({err_type}): {message}")

    return payload


def extract_text_blocks(payload: dict[str, Any]) -> str:
    content = payload.get("content")
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "text":
            continue
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())

    return "\n".join(parts).strip()
