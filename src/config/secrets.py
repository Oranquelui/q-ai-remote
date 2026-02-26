"""Secret accessor facade.

Accounts in OS store:
- codex_api_key
- telegram_bot_token
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.secrets.base import SecretStore, SecretStoreError, require_secret
from src.secrets.factory import create_secret_store


@dataclass(frozen=True)
class RuntimeSecrets:
    telegram_bot_token: str
    codex_api_key: Optional[str]


def _optional_secret(store: SecretStore, account: str) -> Optional[str]:
    try:
        return store.get_secret(account)
    except SecretStoreError:
        return None


def load_runtime_secrets(
    service_name: str = "qcodeanzenn",
    require_codex_api_key: bool = True,
) -> RuntimeSecrets:
    store = create_secret_store(service_name=service_name)
    codex_api_key: Optional[str]
    if require_codex_api_key:
        codex_api_key = require_secret(store, "codex_api_key")
    else:
        codex_api_key = _optional_secret(store=store, account="codex_api_key")

    return RuntimeSecrets(
        telegram_bot_token=require_secret(store, "telegram_bot_token"),
        codex_api_key=codex_api_key,
    )


__all__ = ["RuntimeSecrets", "load_runtime_secrets", "SecretStoreError"]
