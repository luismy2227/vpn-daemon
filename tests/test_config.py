from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from vpn_daemon.config import (
    Config,
    CredentialsMissingError,
    _resolve_path,
    default_config_path,
    load_config,
)

_FULL_JSON = {
    "username": "user@example.com",
    "password": "pin123",
    "totp_secret": "JBSWY3DPEHPK3PXP",
    "openvpn_path": r"C:\openvpn\bin\openvpn.exe",
    "profile": "vpn.ovpn",
}


def _write_cfg(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    # create a dummy profile so load_config doesn't fail on path resolution
    (tmp_path / "vpn.ovpn").touch()
    return p


def test_load_config_full(tmp_path):
    cfg_path = _write_cfg(tmp_path, _FULL_JSON)
    cfg = load_config(cfg_path)
    assert isinstance(cfg, Config)
    assert cfg.username == "user@example.com"
    assert cfg.password == "pin123"
    assert cfg.totp_secret == "JBSWY3DPEHPK3PXP"
    assert cfg.use_management is True   # default
    assert cfg.auto_connect is False    # default


def test_load_config_defaults(tmp_path):
    cfg_path = _write_cfg(tmp_path, _FULL_JSON)
    cfg = load_config(cfg_path)
    assert cfg.management_host == "127.0.0.1"
    assert cfg.management_port == 7505
    assert cfg.strip_profile_management is True
    assert cfg.internal_ping_host is None
    assert cfg.log_directory is None


def test_load_config_missing_credentials_falls_back_to_keyring(tmp_path, monkeypatch):
    data = {k: v for k, v in _FULL_JSON.items() if k not in ("username", "password", "totp_secret")}
    cfg_path = _write_cfg(tmp_path, data)

    import vpn_daemon.credentials as creds_mod
    monkeypatch.setattr(creds_mod, "load_credentials",
                        lambda: ("kr_user", "kr_pass", "JBSWY3DPEHPK3PXP"))

    cfg = load_config(cfg_path)
    assert cfg.username == "kr_user"
    assert cfg.password == "kr_pass"


def test_load_config_missing_credentials_no_keyring_raises(tmp_path, monkeypatch):
    data = {k: v for k, v in _FULL_JSON.items() if k not in ("username", "password", "totp_secret")}
    cfg_path = _write_cfg(tmp_path, data)

    import vpn_daemon.credentials as creds_mod
    monkeypatch.setattr(creds_mod, "load_credentials", lambda: None)

    with pytest.raises(CredentialsMissingError):
        load_config(cfg_path)


def test_load_config_missing_required_key(tmp_path):
    data = dict(_FULL_JSON)
    del data["profile"]
    cfg_path = _write_cfg(tmp_path, data)
    with pytest.raises(KeyError):
        load_config(cfg_path)


def test_load_config_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nonexistent.json")


def test_default_config_path_env(monkeypatch, tmp_path):
    p = tmp_path / "custom.json"
    monkeypatch.setenv("VPN_DAEMON_CONFIG", str(p))
    assert default_config_path() == p.resolve()


def test_default_config_path_default(monkeypatch):
    monkeypatch.delenv("VPN_DAEMON_CONFIG", raising=False)
    result = default_config_path()
    assert result.name == "config.json"
    assert result.parent.name == "config"


def test_resolve_path_absolute(tmp_path):
    abs_path = tmp_path / "file.txt"
    assert _resolve_path(tmp_path, abs_path) == abs_path.resolve()


def test_resolve_path_relative(tmp_path):
    result = _resolve_path(tmp_path, "sub/file.txt")
    assert result == (tmp_path / "sub" / "file.txt").resolve()
