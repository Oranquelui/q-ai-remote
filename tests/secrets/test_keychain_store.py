from src.secrets.keychain_store import KeychainSecretStore


def test_keychain_store_class_exists() -> None:
    assert KeychainSecretStore is not None
