"""Factory for selecting planner engine implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.adapters.claude_subscription_client import ClaudeSubscriptionClient
from src.adapters.codex_client import CodexClient
from src.adapters.codex_subscription_client import CodexSubscriptionClient
from src.adapters.plan_client import PlanDraftClient
from src.config.policy import PolicyConfig


class PlannerFactoryError(RuntimeError):
    """Planner engine initialization error."""


def create_planner_client(
    policy: PolicyConfig,
    workspace_root: Path,
    codex_api_key: Optional[str],
) -> PlanDraftClient:
    mode = policy.engine.mode

    if mode == "codex_api":
        if not codex_api_key:
            raise PlannerFactoryError("codex_api mode requires codex_api_key in OS credential store")
        return CodexClient(
            api_key=codex_api_key,
            model=policy.engine.codex_api_model,
        )

    if mode == "codex_subscription":
        return CodexSubscriptionClient(
            command=policy.engine.codex_cli.command,
            model=policy.engine.codex_cli.model,
            timeout_seconds=policy.engine.timeout_seconds,
            workdir=workspace_root,
        )

    if mode == "claude_subscription":
        return ClaudeSubscriptionClient(
            command=policy.engine.claude_cli.command,
            model=policy.engine.claude_cli.model,
            timeout_seconds=policy.engine.timeout_seconds,
            workdir=workspace_root,
        )

    raise PlannerFactoryError(f"unsupported engine mode: {mode}")

