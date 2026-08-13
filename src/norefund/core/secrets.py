"""Secure storage for user-supplied API tokens (e.g. a HuggingFace token).

Tokens are stored in the OS-native credential store (Windows Credential
Locker, macOS Keychain, Secret Service/KWallet on Linux) via `keyring` —
never written to `settings.json` or anywhere else on disk in plaintext.
"""

from __future__ import annotations

import logging
from typing import Optional

import keyring
import keyring.errors

_LOG = logging.getLogger(__name__)

_SERVICE_NAME = "NoRefund"
HF_TOKEN_KEY = "hf_token"


def keyring_available() -> bool:
    """Whether a usable OS credential store is available on this machine."""
    try:
        keyring.get_password(_SERVICE_NAME, "__norefund_probe__")
        return True
    except keyring.errors.KeyringError:
        return False


def get_hf_token() -> str | None:
    """Return the stored HuggingFace token, or None if unset/unavailable."""
    try:
        return keyring.get_password(_SERVICE_NAME, HF_TOKEN_KEY)
    except keyring.errors.KeyringError as exc:
        _LOG.warning("keyring_read_failed", extra={"ctx": {"error": str(exc)}})
        return None


def set_hf_token(token: str) -> None:
    keyring.set_password(_SERVICE_NAME, HF_TOKEN_KEY, token)


def delete_hf_token() -> None:
    try:
        keyring.delete_password(_SERVICE_NAME, HF_TOKEN_KEY)
    except keyring.errors.PasswordDeleteError:
        pass
