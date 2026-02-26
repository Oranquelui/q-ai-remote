import json
import subprocess
from pathlib import Path

import pytest

from src.adapters.claude_subscription_client import ClaudeSubscriptionClient, ClaudeSubscriptionClientError


def test_claude_subscription_client_parses_result_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = {
        "result": json.dumps(
            {
                "ops": [{"type": "read_file", "path": "docs/readme.md"}],
                "summary": "safe read",
            }
        )
    }

    def _fake_run(cmd, cwd, capture_output, text, timeout, check):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("subprocess.run", _fake_run)

    client = ClaudeSubscriptionClient(
        command="claude",
        model="sonnet",
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


def test_claude_subscription_client_raises_on_invalid_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _fake_run(cmd, cwd, capture_output, text, timeout, check):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='{"result":"not-json"}', stderr="")

    monkeypatch.setattr("subprocess.run", _fake_run)

    client = ClaudeSubscriptionClient(
        command="claude",
        model="sonnet",
        timeout_seconds=10,
        workdir=tmp_path,
    )
    with pytest.raises(ClaudeSubscriptionClientError):
        client.draft_plan(
            request_text="READMEを確認したい",
            allowed_ops=["read_file"],
            allowed_prefixes=["docs/"],
        )

