"""Secret store factory based on OS."""

from __future__ import annotations

import platform

from src.secrets.base import SecretStore, SecretStoreError
from src.secrets.credman_store import CredManSecretStore
from src.secrets.keychain_store import KeychainSecretStore


def create_secret_store(service_name: str = "qcodeanzenn") -> SecretStore:
    system = platform.system().lower()
    if system == "darwin":
        return KeychainSecretStore(service_name=service_name)
    if system == "windows":
        return CredManSecretStore(service_name=service_name)
    raise SecretStoreError(
        f"unsupported OS for MVP secret storage: {platform.system()} "
        "(supported: macOS, Windows)"
    )
