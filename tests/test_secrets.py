from __future__ import annotations

import keyring
import keyring.errors
import pytest

from norefund.core import secrets


class _FakeKeyring(keyring.backend.KeyringBackend):
    priority = 1

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service, username):
        return self._store.get((service, username))

    def set_password(self, service, username, password):
        self._store[(service, username)] = password

    def delete_password(self, service, username):
        if (service, username) not in self._store:
            raise keyring.errors.PasswordDeleteError("not found")
        del self._store[(service, username)]


class _BrokenKeyring(keyring.backend.KeyringBackend):
    priority = 1

    def get_password(self, service, username):
        raise keyring.errors.NoKeyringError("no backend available")

    def set_password(self, service, username, password):
        raise keyring.errors.NoKeyringError("no backend available")

    def delete_password(self, service, username):
        raise keyring.errors.NoKeyringError("no backend available")


@pytest.fixture
def fake_keyring(monkeypatch):
    backend = _FakeKeyring()
    monkeypatch.setattr(keyring, "set_keyring", keyring.set_keyring)
    keyring.set_keyring(backend)
    yield backend


@pytest.fixture
def broken_keyring(monkeypatch):
    keyring.set_keyring(_BrokenKeyring())
    yield


def test_get_hf_token_returns_none_when_unset(fake_keyring):
    assert secrets.get_hf_token() is None


def test_set_then_get_hf_token_roundtrip(fake_keyring):
    secrets.set_hf_token("hf_abc123")
    assert secrets.get_hf_token() == "hf_abc123"


def test_delete_hf_token_removes_it(fake_keyring):
    secrets.set_hf_token("hf_abc123")
    secrets.delete_hf_token()
    assert secrets.get_hf_token() is None


def test_delete_hf_token_when_unset_does_not_raise(fake_keyring):
    secrets.delete_hf_token()


def test_keyring_available_true_with_working_backend(fake_keyring):
    assert secrets.keyring_available() is True


def test_keyring_available_false_without_backend(broken_keyring):
    assert secrets.keyring_available() is False


def test_get_hf_token_returns_none_without_backend(broken_keyring):
    assert secrets.get_hf_token() is None
