"""Codex CLI adapter for subscription users.

This adapter uses `codex exec` in read-only mode and requests strict JSON output.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
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
                    "type": {"type": "string"},
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


class CodexSubscriptionClientError(RuntimeError):
    """Codex CLI interaction error."""


class CodexSubscriptionClient:
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
        schema_path = self._write_tmp_json(_PLAN_SCHEMA, prefix="qca_codex_schema_")
        output_path = self._create_tmp_path(prefix="qca_codex_output_")
        try:
            proc, output_text = self._run_once(
                prompt=prompt,
                schema_path=schema_path,
                output_path=output_path,
                include_model=True,
            )
            if proc.returncode != 0 and self._should_retry_without_model(proc):
                proc, output_text = self._run_once(
                    prompt=prompt,
                    schema_path=schema_path,
                    output_path=output_path,
                    include_model=False,
                )
            if proc.returncode != 0:
                detail = self._tail(proc.stderr or proc.stdout or output_text)
                raise CodexSubscriptionClientError(f"codex CLI failed: {detail}")
            payload = self._extract_payload(output_text)
            return self._to_draft_plan(payload)
        finally:
            self._unlink_if_exists(schema_path)
            self._unlink_if_exists(output_path)

    def _build_command(
        self,
        prompt: str,
        schema_path: Path,
        output_path: Path,
        include_model: bool,
    ) -> list[str]:
        cmd = [
            self._command,
            "exec",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(output_path),
        ]
        if include_model and self._model:
            cmd.extend(["--model", self._model])
        cmd.append(prompt)
        return cmd

    def _run_once(
        self,
        prompt: str,
        schema_path: Path,
        output_path: Path,
        include_model: bool,
    ) -> tuple[subprocess.CompletedProcess, str]:
        cmd = self._build_command(
            prompt=prompt,
            schema_path=schema_path,
            output_path=output_path,
            include_model=include_model,
        )
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
            raise CodexSubscriptionClientError(
                "codex CLI not found. Install Codex CLI and run `codex login`."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise CodexSubscriptionClientError("codex CLI timed out while drafting plan") from exc

        output_text = output_path.read_text(encoding="utf-8").strip()
        if not output_text:
            output_text = proc.stdout.strip()
        return proc, output_text

    @staticmethod
    def _should_retry_without_model(proc: subprocess.CompletedProcess) -> bool:
        detail = f"{proc.stderr or ''}\n{proc.stdout or ''}".lower()
        return (
            "reasoning.effort" in detail
            and "unsupported_value" in detail
            and "xhigh" in detail
        )

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
        text = output_text.strip()
        if not text:
            raise CodexSubscriptionClientError("codex CLI returned empty response")

        payload = CodexSubscriptionClient._load_json(text)
        if payload is None:
            raise CodexSubscriptionClientError("codex CLI response is not valid JSON")

        if isinstance(payload, dict) and "ops" in payload and "summary" in payload:
            return payload

        if isinstance(payload, dict) and "result" in payload:
            result = payload.get("result")
            if isinstance(result, dict):
                return result
            if isinstance(result, str):
                parsed = CodexSubscriptionClient._load_json(result)
                if isinstance(parsed, dict):
                    return parsed

        if isinstance(payload, dict) and "structured_output" in payload:
            so = payload.get("structured_output")
            if isinstance(so, dict):
                return so

        raise CodexSubscriptionClientError("codex CLI response missing required fields: ops/summary")

    @staticmethod
    def _to_draft_plan(payload: dict[str, Any]) -> DraftPlan:
        ops = payload.get("ops")
        summary = payload.get("summary", "")
        if not isinstance(ops, list):
            raise CodexSubscriptionClientError("codex CLI payload 'ops' must be an array")
        if not isinstance(summary, str):
            raise CodexSubscriptionClientError("codex CLI payload 'summary' must be a string")
        return DraftPlan(ops=ops, summary=summary.strip())

    @staticmethod
    def _write_tmp_json(data: dict[str, Any], prefix: str) -> Path:
        fd, path = tempfile.mkstemp(prefix=prefix, suffix=".json")
        os.close(fd)
        tmp_path = Path(path)
        tmp_path.write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8")
        return tmp_path

    @staticmethod
    def _create_tmp_path(prefix: str) -> Path:
        fd, path = tempfile.mkstemp(prefix=prefix, suffix=".json")
        os.close(fd)
        return Path(path)

    @staticmethod
    def _unlink_if_exists(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    @staticmethod
    def _load_json(text: str) -> Optional[Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Some CLIs may stream additional lines; try last JSON line.
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
    def _tail(text: str, limit: int = 500) -> str:
        clean = (text or "").strip()
        if len(clean) <= limit:
            return clean
        return clean[-limit:]
