import pytest

from src.config.secrets import load_runtime_secrets
from src.secrets.base import SecretStoreError


class _DummyStore:
    def __init__(self, values: dict[str, str]) -> None:
        self._values = values

    def get_secret(self, account: str) -> str:
        if account not in self._values:
            raise SecretStoreError(f"missing: {account}")
        return self._values[account]


def test_load_runtime_secrets_codex_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.config.secrets.create_secret_store",
        lambda service_name: _DummyStore({"telegram_bot_token": "tg_token"}),
    )

    secrets = load_runtime_secrets(require_codex_api_key=False)
    assert secrets.telegram_bot_token == "tg_token"
    assert secrets.codex_api_key is None


def test_load_runtime_secrets_codex_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.config.secrets.create_secret_store",
        lambda service_name: _DummyStore({"telegram_bot_token": "tg_token"}),
    )

    with pytest.raises(SecretStoreError):
        load_runtime_secrets(require_codex_api_key=True)

