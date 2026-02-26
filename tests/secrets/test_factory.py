import platform

import pytest

from src.secrets.base import SecretStoreError
from src.secrets.factory import create_secret_store


def test_factory_supports_known_os(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    store = create_secret_store()
    assert store is not None


def test_factory_rejects_unknown_os(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    with pytest.raises(SecretStoreError):
        create_secret_store()
