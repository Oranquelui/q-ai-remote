"""Windows Credential Manager adapter."""

from __future__ import annotations

import importlib

from src.secrets.base import SecretStore, SecretStoreError


class CredManSecretStore(SecretStore):
    def __init__(self, service_name: str) -> None:
        self._service_name = service_name
        try:
            self._keyring = importlib.import_module("keyring")
        except Exception as exc:  # pragma: no cover - import guarded at runtime
            raise SecretStoreError("keyring package is required for Credential Manager access") from exc

    def get_secret(self, account: str) -> str:
        try:
            value = self._keyring.get_password(self._service_name, account)
        except Exception as exc:
            raise SecretStoreError(f"failed to read Credential Manager secret '{account}'") from exc
        if not value:
            raise SecretStoreError(f"missing Credential Manager secret '{account}'")
        return value
