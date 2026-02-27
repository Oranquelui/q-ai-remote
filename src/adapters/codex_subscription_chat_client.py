"""Codex CLI adapter for free-text Q&A (subscription mode)."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


_SYSTEM_PROMPT = (
    "You are Q CodeAnzenn chat assistant.\n"
    "Rules:\n"
    "- Answer as chat only. Do not execute files or shell commands.\n"
    "- You may use live external web sources for facts (weather/news/prices/docs) when available.\n"
    "- If live web access is unavailable in this runtime, clearly state that limitation instead of guessing.\n"
    "- If user asks code or file changes, tell them to use /task for Plan+Risk flow.\n"
    "- Keep answer concise and practical.\n\n"
)


class CodexSubscriptionChatClientError(RuntimeError):
    """Codex CLI chat interaction error."""


class CodexSubscriptionChatClient:
    def __init__(self, command: str, model: str, timeout_seconds: int, workdir: Path) -> None:
        self._command = command
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._workdir = workdir.resolve()

    def answer(self, user_text: str) -> str:
        prompt = (user_text or "").strip()
        if not prompt:
            return "質問を入力してください。"
        output_path = self._create_tmp_path(prefix="qca_codex_chat_")
        try:
            cmd = [
                self._command,
                "exec",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--output-last-message",
                str(output_path),
            ]
            if self._model:
                cmd.extend(["--model", self._model])
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
                raise CodexSubscriptionChatClientError(
                    "codex CLI not found. Install Codex CLI and run `codex login`."
                ) from exc
            except subprocess.TimeoutExpired as exc:
                raise CodexSubscriptionChatClientError("codex CLI timed out while generating chat answer") from exc

            text = output_path.read_text(encoding="utf-8").strip()
            if not text:
                text = (proc.stdout or "").strip()
            if proc.returncode != 0:
                detail = self._tail(proc.stderr or proc.stdout or text)
                raise CodexSubscriptionChatClientError(f"codex CLI failed: {detail}")
            if not text:
                raise CodexSubscriptionChatClientError("codex CLI returned empty chat response")
            return text
        finally:
            try:
                output_path.unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _create_tmp_path(prefix: str) -> Path:
        fd, path = tempfile.mkstemp(prefix=prefix, suffix=".txt")
        os.close(fd)
        return Path(path)

    @staticmethod
    def _tail(text: str, limit: int = 400) -> str:
        clean = (text or "").strip()
        if len(clean) <= limit:
            return clean
        return clean[-limit:]
