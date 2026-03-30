"""Windows Credential Manager wrapper for VPN daemon secrets."""

from __future__ import annotations

import keyring
import keyring.errors

_SERVICE = "vpn-daemon"
_KEYS = ("username", "password", "totp_secret")


def save_credentials(username: str, password: str, totp_secret: str) -> None:
    keyring.set_password(_SERVICE, "username", username)
    keyring.set_password(_SERVICE, "password", password)
    keyring.set_password(_SERVICE, "totp_secret", totp_secret)


def load_credentials() -> tuple[str, str, str] | None:
    """Return (username, password, totp_secret) or None if any are missing."""
    values = [keyring.get_password(_SERVICE, k) for k in _KEYS]
    if any(v is None for v in values):
        return None
    return values[0], values[1], values[2]  # type: ignore[return-value]


def credentials_exist() -> bool:
    return load_credentials() is not None


def clear_credentials() -> None:
    for k in _KEYS:
        try:
            keyring.delete_password(_SERVICE, k)
        except keyring.errors.PasswordDeleteError:
            pass
