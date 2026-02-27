"""Claude API adapter for free-text Q&A."""

from __future__ import annotations

from src.adapters.claude_api_http import ClaudeApiHttpError, extract_text_blocks, request_claude_message


_SYSTEM_PROMPT = (
    "You are Q CodeAnzenn chat assistant. "
    "Answer user questions in plain language. "
    "Do not execute files or shell commands. "
    "You may use live external web sources for facts (weather/news/prices/docs) when available. "
    "If live web access is unavailable in this runtime, clearly state that limitation instead of guessing. "
    "If user asks code/file changes, direct them to /task flow."
)


class ClaudeApiChatClientError(RuntimeError):
    """Claude API chat interaction error."""


class ClaudeApiChatClient:
    def __init__(self, api_key: str, model: str = "claude-3-7-sonnet-latest", timeout_seconds: int = 120) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    def answer(self, user_text: str) -> str:
        prompt = (user_text or "").strip()
        if not prompt:
            return "質問を入力してください。"

        try:
            payload = request_claude_message(
                api_key=self._api_key,
                model=self._model,
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=prompt,
                max_tokens=900,
                timeout_seconds=self._timeout_seconds,
            )
        except ClaudeApiHttpError as exc:
            raise ClaudeApiChatClientError(str(exc)) from exc

        text = extract_text_blocks(payload)
        if not text:
            raise ClaudeApiChatClientError("Claude API returned empty chat response")
        return text
