"""Security regression anchors for MVP."""

from pathlib import Path


def test_allowed_paths_policy_flags_exist() -> None:
    text = Path("config/policy.yaml").read_text(encoding="utf-8")
    assert "reject_parent_traversal: true" in text
    assert "reject_symlink: true" in text
    assert "reject_junction: true" in text


def test_preapprove_guard_exists_in_executor() -> None:
    text = Path("src/core/executor.py").read_text(encoding="utf-8")
    assert "plan is not executable from status=" in text


def test_secret_loader_does_not_use_env_fallback() -> None:
    text = Path("src/config/secrets.py").read_text(encoding="utf-8")
    assert "os.getenv" not in text


def test_executor_has_no_http_client_import() -> None:
    text = Path("src/core/executor.py").read_text(encoding="utf-8")
    assert "requests" not in text
    assert "httpx" not in text
