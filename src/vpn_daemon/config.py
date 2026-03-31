from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CredentialsMissingError(RuntimeError):
    """Raised when credentials are absent from both config.json and the keyring."""


@dataclass
class Config:
    username: str
    password: str
    totp_secret: str
    openvpn_path: Path
    profile: Path
    use_management: bool = True
    management_host: str = "127.0.0.1"
    management_port: int = 7505
    strip_profile_management: bool = True
    management_hold_release: bool = True
    internal_ping_host: str | None = None
    log_directory: Path | None = None
    tray_tooltip: str = "VPN — right-click for menu"
    auto_connect: bool = False
    notify_on_action: bool = False


def default_config_path() -> Path:
    env = os.environ.get("VPN_DAEMON_CONFIG")
    if env:
        return Path(env).expanduser().resolve()
    # PyInstaller one-file: __file__ lives under %TEMP%\_MEI…; use the .exe directory instead.
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        return (exe_dir / "config" / "config.json").resolve()
    root = Path(__file__).resolve().parents[2]
    return (root / "config" / "config.json").resolve()


def _resolve_path(base: Path, p: str | Path) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path.resolve()
    return (base / path).resolve()


def load_config(path: Path | None = None) -> Config:
    if path is None:
        path = default_config_path()
    else:
        path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Config not found: {path}")

    base = path.parent
    with path.open(encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)

    # Credentials: prefer values in JSON (backward compat), fall back to keyring.
    username = raw.get("username")
    password = raw.get("password")
    totp_secret = raw.get("totp_secret")
    if not all([username, password, totp_secret]):
        from vpn_daemon.credentials import load_credentials  # avoid circular at module level
        creds = load_credentials()
        if creds is None:
            raise CredentialsMissingError(
                "Credentials not found in config.json or Windows Credential Manager. "
                "Run the setup wizard to configure them."
            )
        kr_user, kr_pass, kr_totp = creds
        username = username or kr_user
        password = password or kr_pass
        totp_secret = totp_secret or kr_totp

    profile = _resolve_path(base, raw["profile"])
    openvpn = Path(raw["openvpn_path"]).expanduser()
    log_dir = raw.get("log_directory")
    log_path = Path(log_dir).expanduser().resolve() if log_dir else None

    return Config(
        username=str(username),
        password=str(password),
        totp_secret=str(totp_secret),
        openvpn_path=openvpn,
        profile=profile,
        use_management=bool(raw.get("use_management", True)),
        management_host=str(raw.get("management_host", "127.0.0.1")),
        management_port=int(raw.get("management_port", 7505)),
        strip_profile_management=bool(raw.get("strip_profile_management", True)),
        management_hold_release=bool(raw.get("management_hold_release", True)),
        internal_ping_host=raw.get("internal_ping_host"),
        log_directory=log_path,
        tray_tooltip=str(raw.get("tray_tooltip", "VPN — right-click for menu")),
        auto_connect=bool(raw.get("auto_connect", False)),
        notify_on_action=bool(raw.get("notify_on_action", False)),
    )
