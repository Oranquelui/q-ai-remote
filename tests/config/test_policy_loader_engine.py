from pathlib import Path

import pytest
import yaml

from src.config.policy import PolicyLoadError, load_policy


def test_policy_loader_accepts_engine_modes() -> None:
    policy = load_policy(Path("config/policy.yaml"))
    assert policy.engine.mode in {"codex_api", "codex_subscription", "claude_subscription"}


def test_policy_loader_rejects_invalid_engine_mode(tmp_path: Path) -> None:
    src = yaml.safe_load(Path("config/policy.yaml").read_text(encoding="utf-8"))
    src["engine"]["mode"] = "invalid_mode"

    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(src, allow_unicode=False), encoding="utf-8")

    with pytest.raises(PolicyLoadError):
        load_policy(path)


def test_policy_loader_rejects_non_codex_command_in_codex_mode(tmp_path: Path) -> None:
    src = yaml.safe_load(Path("config/policy.yaml").read_text(encoding="utf-8"))
    src["engine"]["mode"] = "codex_subscription"
    src["engine"]["codex_cli"]["command"] = "python"

    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(src, allow_unicode=False), encoding="utf-8")

    with pytest.raises(PolicyLoadError):
        load_policy(path)


def test_policy_loader_rejects_invalid_instance_id(tmp_path: Path) -> None:
    src = yaml.safe_load(Path("config/policy.yaml").read_text(encoding="utf-8"))
    src["instance"] = {"id": "../bad"}

    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(src, allow_unicode=False), encoding="utf-8")

    with pytest.raises(PolicyLoadError):
        load_policy(path)
