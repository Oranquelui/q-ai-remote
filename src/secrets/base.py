"""SecretStore abstractions.

MVP policy: secrets must come from OS credential stores only.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class SecretStoreError(RuntimeError):
    """Raised when a secret cannot be loaded securely."""


class SecretStore(ABC):
    """Credential store interface."""

    @abstractmethod
    def get_secret(self, account: str) -> str:
        """Return secret value for an account or raise SecretStoreError."""


def require_secret(store: SecretStore, account: str) -> str:
    value = store.get_secret(account)
    if not value:
        raise SecretStoreError(f"secret is empty: {account}")
    return value
