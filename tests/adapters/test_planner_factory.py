from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters.claude_subscription_client import ClaudeSubscriptionClient
from src.adapters.codex_subscription_client import CodexSubscriptionClient
from src.adapters.planner_factory import PlannerFactoryError, create_planner_client
from src.config.policy import load_policy


def test_factory_requires_codex_api_key_in_api_mode() -> None:
    policy = load_policy(Path("config/policy.yaml"))
    policy = replace(policy, engine=replace(policy.engine, mode="codex_api"))

    with pytest.raises(PlannerFactoryError):
        create_planner_client(policy=policy, workspace_root=Path("."), codex_api_key=None)


def test_factory_selects_codex_subscription_client() -> None:
    policy = load_policy(Path("config/policy.yaml"))
    policy = replace(policy, engine=replace(policy.engine, mode="codex_subscription"))

    client = create_planner_client(policy=policy, workspace_root=Path("."), codex_api_key=None)
    assert isinstance(client, CodexSubscriptionClient)


def test_factory_selects_claude_subscription_client() -> None:
    policy = load_policy(Path("config/policy.yaml"))
    policy = replace(policy, engine=replace(policy.engine, mode="claude_subscription"))

    client = create_planner_client(policy=policy, workspace_root=Path("."), codex_api_key=None)
    assert isinstance(client, ClaudeSubscriptionClient)
