"""Claude API adapter for plan drafting."""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from src.adapters.claude_api_http import ClaudeApiHttpError, extract_text_blocks, request_claude_message
from src.adapters.plan_client import DraftPlan


class ClaudeApiClientError(RuntimeError):
    """Claude API interaction error."""


class ClaudeApiClient:
    def __init__(self, api_key: str, model: str = "claude-3-7-sonnet-latest", timeout_seconds: int = 120) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    def draft_plan(
        self,
        request_text: str,
        allowed_ops: list[str],
        allowed_prefixes: list[str],
    ) -> DraftPlan:
        system_prompt = (
            "Generate a SAFE filesystem plan only. "
            "Return JSON only with keys: ops (array), summary (string). "
            "Allowed ops: "
            + ", ".join(allowed_ops)
            + ". Paths must be workspace-relative and must stay under allowed prefixes: "
            + ", ".join(allowed_prefixes)
            + ". Never use absolute paths, UNC paths, parent traversal, shell commands, or network/file-transfer operations in the plan itself. "
            "Use create_file only for clearly new paths. If a file may already exist, prefer patch_file."
        )
        user_prompt = (
            "User request:\n"
            + request_text
            + "\n\nOutput JSON example:\n"
            + '{"ops":[{"type":"read_file","path":"docs/README.md","content":null,"patch":null}],"summary":"..."}'
        )

        try:
            payload = request_claude_message(
                api_key=self._api_key,
                model=self._model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=1400,
                timeout_seconds=self._timeout_seconds,
            )
        except ClaudeApiHttpError as exc:
            raise ClaudeApiClientError(str(exc)) from exc

        text = extract_text_blocks(payload)
        if not text:
            raise ClaudeApiClientError("Claude API returned empty response")

        parsed = self._load_json(text)
        if not isinstance(parsed, dict):
            raise ClaudeApiClientError("Claude API response is not valid JSON")

        ops = parsed.get("ops")
        summary = parsed.get("summary", "")
        if not isinstance(ops, list):
            raise ClaudeApiClientError("Claude API response missing ops array")
        if not isinstance(summary, str):
            raise ClaudeApiClientError("Claude API response summary must be string")

        return DraftPlan(ops=ops, summary=summary.strip())

    @staticmethod
    def _load_json(text: str) -> Optional[Any]:
        raw = (text or "").strip()
        if not raw:
            return None

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.IGNORECASE | re.DOTALL)
        if fenced:
            block = fenced.group(1).strip()
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                pass

        for line in reversed(raw.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

        return None
