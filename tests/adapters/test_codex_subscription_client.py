import json
import subprocess
from pathlib import Path

import pytest

from src.adapters.codex_subscription_client import CodexSubscriptionClient, CodexSubscriptionClientError


def test_codex_subscription_client_parses_valid_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _fake_run(cmd, cwd, capture_output, text, timeout, check):  # type: ignore[no-untyped-def]
        out_path = Path(cmd[cmd.index("--output-last-message") + 1])
        out_path.write_text(
            json.dumps(
                {
                    "ops": [{"type": "read_file", "path": "docs/readme.md"}],
                    "summary": "safe read",
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", _fake_run)

    client = CodexSubscriptionClient(
        command="codex",
        model="gpt-5-codex",
        timeout_seconds=10,
        workdir=tmp_path,
    )
    draft = client.draft_plan(
        request_text="READMEを確認したい",
        allowed_ops=["read_file"],
        allowed_prefixes=["docs/"],
    )
    assert draft.summary == "safe read"
    assert draft.ops[0]["path"] == "docs/readme.md"


def test_codex_subscription_client_raises_on_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _fake_run(cmd, cwd, capture_output, text, timeout, check):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(args=cmd, returncode=2, stdout="", stderr="failed")

    monkeypatch.setattr("subprocess.run", _fake_run)

    client = CodexSubscriptionClient(
        command="codex",
        model="gpt-5-codex",
        timeout_seconds=10,
        workdir=tmp_path,
    )
    with pytest.raises(CodexSubscriptionClientError):
        client.draft_plan(
            request_text="READMEを確認したい",
            allowed_ops=["read_file"],
            allowed_prefixes=["docs/"],
        )

