"""Factory for selecting chat engine implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.adapters.claude_api_chat_client import ClaudeApiChatClient
from src.adapters.chat_client import ChatAnswerClient
from src.adapters.claude_subscription_chat_client import ClaudeSubscriptionChatClient
from src.adapters.codex_chat_client import CodexChatClient
from src.adapters.codex_subscription_chat_client import CodexSubscriptionChatClient
from src.config.policy import PolicyConfig


class ChatFactoryError(RuntimeError):
    """Chat engine initialization error."""


def create_chat_client(
    policy: PolicyConfig,
    workspace_root: Path,
    codex_api_key: Optional[str],
    claude_api_key: Optional[str] = None,
) -> ChatAnswerClient:
    mode = policy.engine.mode

    if mode == "codex_api":
        if not codex_api_key:
            raise ChatFactoryError("codex_api mode requires codex_api_key in OS credential store")
        return CodexChatClient(api_key=codex_api_key, model=policy.engine.codex_api_model)

    if mode == "claude_api":
        if not claude_api_key:
            raise ChatFactoryError("claude_api mode requires claude_api_key in OS credential store")
        return ClaudeApiChatClient(
            api_key=claude_api_key,
            model=policy.engine.claude_api_model,
            timeout_seconds=policy.engine.timeout_seconds,
        )

    if mode == "codex_subscription":
        return CodexSubscriptionChatClient(
            command=policy.engine.codex_cli.command,
            model=policy.engine.codex_cli.model,
            timeout_seconds=policy.engine.timeout_seconds,
            workdir=workspace_root,
        )

    if mode == "claude_subscription":
        return ClaudeSubscriptionChatClient(
            command=policy.engine.claude_cli.command,
            model=policy.engine.claude_cli.model,
            timeout_seconds=policy.engine.timeout_seconds,
            workdir=workspace_root,
        )

    raise ChatFactoryError(f"unsupported engine mode: {mode}")
