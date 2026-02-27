"""Claude CLI adapter for subscription users."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Optional

from src.adapters.plan_client import DraftPlan


_PLAN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "ops": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["list_dir", "read_file", "create_file", "patch_file"],
                    },
                    "path": {"type": "string"},
                    "content": {"type": ["string", "null"]},
                    "patch": {"type": ["string", "null"]},
                },
                "required": ["type", "path", "content", "patch"],
            },
        },
        "summary": {"type": "string"},
    },
    "required": ["ops", "summary"],
}


class ClaudeSubscriptionClientError(RuntimeError):
    """Claude CLI interaction error."""


class ClaudeSubscriptionClient:
    def __init__(
        self,
        command: str,
        model: str,
        timeout_seconds: int,
        workdir: Path,
    ) -> None:
        self._command = command
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._workdir = workdir.resolve()

    def draft_plan(
        self,
        request_text: str,
        allowed_ops: list[str],
        allowed_prefixes: list[str],
    ) -> DraftPlan:
        prompt = self._build_prompt(
            request_text=request_text,
            allowed_ops=allowed_ops,
            allowed_prefixes=allowed_prefixes,
        )
        cmd = [
            self._command,
            "-p",
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(_PLAN_SCHEMA, ensure_ascii=True),
            "--tools",
            "",
            "--no-session-persistence",
            "--disable-slash-commands",
        ]
        if self._model:
            cmd.extend(["--model", self._model])
        cmd.append(prompt)

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
            raise ClaudeSubscriptionClientError(
                "claude CLI not found. Install Claude Code and complete `claude auth`."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ClaudeSubscriptionClientError("claude CLI timed out while drafting plan") from exc

        if proc.returncode != 0:
            detail = self._tail(proc.stderr or proc.stdout)
            raise ClaudeSubscriptionClientError(f"claude CLI failed: {detail}")

        payload = self._extract_payload(proc.stdout)
        return self._to_draft_plan(payload)

    @staticmethod
    def _build_prompt(request_text: str, allowed_ops: list[str], allowed_prefixes: list[str]) -> str:
        return (
            "Generate a SAFE filesystem plan only.\n"
            "Return JSON with keys: ops (array), summary (string).\n"
            "Allowed ops: "
            + ", ".join(allowed_ops)
            + "\nAllowed path prefixes: "
            + ", ".join(allowed_prefixes)
            + "\nConstraints: workspace-relative paths only; no absolute paths; no UNC paths; "
            "no parent traversal; no shell commands; no network/file-transfer operations in the plan itself. "
            "Use create_file only for clearly new paths. If a file may already exist, prefer patch_file.\n"
            "User request:\n"
            + request_text
        )

    @staticmethod
    def _extract_payload(output_text: str) -> dict[str, Any]:
        payload = ClaudeSubscriptionClient._load_json(output_text)
        if payload is None:
            raise ClaudeSubscriptionClientError("claude CLI output is not valid JSON")

        if isinstance(payload, dict) and "ops" in payload and "summary" in payload:
            return payload

        if isinstance(payload, dict):
            so = payload.get("structured_output")
            if isinstance(so, dict):
                return so

            result = payload.get("result")
            if isinstance(result, dict):
                return result
            if isinstance(result, str):
                parsed = ClaudeSubscriptionClient._load_json(result)
                if isinstance(parsed, dict):
                    return parsed

            content = payload.get("content")
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    part_text = part.get("text")
                    if isinstance(part_text, str):
                        text_parts.append(part_text)
                joined = "\n".join(text_parts).strip()
                parsed = ClaudeSubscriptionClient._load_json(joined)
                if isinstance(parsed, dict):
                    return parsed

        raise ClaudeSubscriptionClientError("claude CLI response missing required fields: ops/summary")

    @staticmethod
    def _to_draft_plan(payload: dict[str, Any]) -> DraftPlan:
        ops = payload.get("ops")
        summary = payload.get("summary", "")
        if not isinstance(ops, list):
            raise ClaudeSubscriptionClientError("claude CLI payload 'ops' must be an array")
        if not isinstance(summary, str):
            raise ClaudeSubscriptionClientError("claude CLI payload 'summary' must be a string")
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

        for line in reversed(raw.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
        return None

    @staticmethod
    def _tail(text: str, limit: int = 500) -> str:
        clean = (text or "").strip()
        if len(clean) <= limit:
            return clean
        return clean[-limit:]
