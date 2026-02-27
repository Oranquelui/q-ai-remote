"""Claude CLI adapter for free-text Q&A (subscription mode)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Optional


_SYSTEM_PROMPT = (
    "You are Q CodeAnzenn chat assistant.\n"
    "Rules:\n"
    "- Answer as chat only. Do not execute files or shell commands.\n"
    "- You may use live external web sources for facts (weather/news/prices/docs) when available.\n"
    "- If live web access is unavailable in this runtime, clearly state that limitation instead of guessing.\n"
    "- If user asks code or file changes, tell them to use /task for Plan+Risk flow.\n"
    "- Keep answer concise and practical.\n\n"
)


class ClaudeSubscriptionChatClientError(RuntimeError):
    """Claude CLI chat interaction error."""


class ClaudeSubscriptionChatClient:
    def __init__(self, command: str, model: str, timeout_seconds: int, workdir: Path) -> None:
        self._command = command
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._workdir = workdir.resolve()

    def answer(self, user_text: str) -> str:
        prompt = (user_text or "").strip()
        if not prompt:
            return "質問を入力してください。"

        cmd = [
            self._command,
            "-p",
            "--output-format",
            "json",
            "--no-session-persistence",
            "--disable-slash-commands",
            "--allowedTools",
            "WebSearch,WebFetch",
        ]
        if self._model:
            cmd.extend(["--model", self._model])
        cmd.append("--")
        cmd.append(_SYSTEM_PROMPT + "User question:\n" + prompt)

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self._workdir),
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ClaudeSubscriptionChatClientError(
                "claude CLI not found. Install Claude Code and run `claude auth login`."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ClaudeSubscriptionChatClientError("claude CLI timed out while generating chat answer") from exc

        if proc.returncode != 0:
            detail = self._tail(proc.stderr or proc.stdout)
            raise ClaudeSubscriptionChatClientError(f"claude CLI failed: {detail}")

        text = self._extract_text(proc.stdout)
        if not text:
            raise ClaudeSubscriptionChatClientError("claude CLI returned empty chat response")
        return text

    @staticmethod
    def _extract_text(output_text: str) -> str:
        raw = (output_text or "").strip()
        if not raw:
            return ""

        payload = ClaudeSubscriptionChatClient._load_json(raw)
        if payload is None:
            return raw

        if isinstance(payload, str):
            return payload.strip()
        if not isinstance(payload, dict):
            return raw

        result = payload.get("result")
        if isinstance(result, str) and result.strip():
            return result.strip()

        content = payload.get("content")
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                part_text = part.get("text")
                if isinstance(part_text, str) and part_text.strip():
                    parts.append(part_text.strip())
            if parts:
                return "\n".join(parts).strip()

        text = payload.get("output_text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        return raw

    @staticmethod
    def _load_json(text: str) -> Optional[Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        for line in reversed(text.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
        return None

    @staticmethod
    def _tail(text: str, limit: int = 400) -> str:
        clean = (text or "").strip()
        if len(clean) <= limit:
            return clean
        return clean[-limit:]
