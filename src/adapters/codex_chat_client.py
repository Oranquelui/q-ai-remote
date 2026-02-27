"""Codex API adapter for free-text Q&A."""

from __future__ import annotations

import importlib


_SYSTEM_PROMPT = (
    "You are Q CodeAnzenn chat assistant. "
    "Answer user questions in plain language. "
    "Do not execute files or shell commands. "
    "You may use live external web sources for facts (weather/news/prices/docs) when available. "
    "If live web access is unavailable in this runtime, clearly state that limitation instead of guessing. "
    "If user asks code/file changes, direct them to /task flow."
)


class CodexChatClientError(RuntimeError):
    """Codex API chat interaction error."""


class CodexChatClient:
    def __init__(self, api_key: str, model: str = "gpt-5-codex") -> None:
        try:
            openai_mod = importlib.import_module("openai")
        except Exception as exc:
            raise CodexChatClientError("openai package is required") from exc
        self._client = openai_mod.OpenAI(api_key=api_key)
        self._model = model

    def answer(self, user_text: str) -> str:
        prompt = (user_text or "").strip()
        if not prompt:
            return "質問を入力してください。"
        try:
            resp = self._client.responses.create(
                model=self._model,
                input=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_output_tokens=600,
            )
        except Exception as exc:
            raise CodexChatClientError("failed to call Codex API for chat answer") from exc

        text = (getattr(resp, "output_text", "") or "").strip()
        if not text:
            raise CodexChatClientError("Codex API returned empty chat response")
        return text
