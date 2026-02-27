"""Codex API adapter for plan drafting.

This adapter never executes filesystem operations.
It only returns a structured draft plan.
"""

from __future__ import annotations

import importlib
import json

from src.adapters.plan_client import DraftPlan


class CodexClientError(RuntimeError):
    """Codex API interaction error."""


class CodexClient:
    def __init__(self, api_key: str, model: str = "gpt-5-codex") -> None:
        self._api_key = api_key
        self._model = model
        try:
            openai_mod = importlib.import_module("openai")
        except Exception as exc:
            raise CodexClientError("openai package is required") from exc

        self._client = openai_mod.OpenAI(api_key=api_key)

    def draft_plan(
        self,
        request_text: str,
        allowed_ops: list[str],
        allowed_prefixes: list[str],
    ) -> DraftPlan:
        system_prompt = (
            "You are generating a SAFE filesystem plan. "
            "Return JSON only with keys: ops (array), summary (string). "
            "Allowed ops: "
            + ", ".join(allowed_ops)
            + ". Paths must be workspace-relative and must stay under allowed prefixes: "
            + ", ".join(allowed_prefixes)
            + ". Never use absolute paths, UNC paths, parent traversal, shell commands, or network actions. "
            "Use create_file only for clearly new paths. If a file may already exist, prefer patch_file."
        )

        user_prompt = (
            "User request:\n"
            + request_text
            + "\n\nOutput JSON example:\n"
            + '{"ops":[{"type":"read_file","path":"docs/README.md"}],"summary":"..."}'
        )

        try:
            resp = self._client.responses.create(
                model=self._model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_output_tokens=1200,
            )
        except Exception as exc:
            raise CodexClientError("failed to call Codex API") from exc

        text = getattr(resp, "output_text", "")
        if not text:
            raise CodexClientError("Codex API returned empty response")

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CodexClientError("Codex response is not valid JSON") from exc

        ops = payload.get("ops")
        summary = payload.get("summary", "")
        if not isinstance(ops, list):
            raise CodexClientError("Codex response missing ops array")
        if not isinstance(summary, str):
            raise CodexClientError("Codex response summary must be string")

        return DraftPlan(ops=ops, summary=summary.strip())
