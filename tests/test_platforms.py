from __future__ import annotations

import logging
import sys
from unittest.mock import MagicMock, patch

from vpn_daemon.platforms.darwin import DarwinBackend
from vpn_daemon.platforms.linux import LinuxBackend
from vpn_daemon.platforms.windows import WindowsBackend


def test_get_platform_backend_windows():
    with patch.object(sys, "platform", "win32"):
        from vpn_daemon.platforms import get_platform_backend

        b = get_platform_backend()
        assert type(b) is WindowsBackend


def test_get_platform_backend_darwin():
    with patch.object(sys, "platform", "darwin"):
        from vpn_daemon.platforms import get_platform_backend

        b = get_platform_backend()
        assert type(b) is DarwinBackend


def test_get_platform_backend_linux():
    with patch.object(sys, "platform", "linux"):
        from vpn_daemon.platforms import get_platform_backend

        b = get_platform_backend()
        assert type(b) is LinuxBackend


def test_get_platform_backend_unknown_warns_and_uses_linux(caplog):
    with patch.object(sys, "platform", "freebsd14"):
        from vpn_daemon.platforms import get_platform_backend

        with caplog.at_level(logging.WARNING):
            b = get_platform_backend()
    assert type(b) is LinuxBackend
    assert "Unknown sys.platform" in caplog.text


def test_windows_ping_reachable_invokes_ping(monkeypatch):
    called: dict = {}

    def fake_run(args, **kwargs):
        called["args"] = args
        called["kwargs"] = kwargs
        return MagicMock(returncode=0)

    monkeypatch.setattr("vpn_daemon.platforms.windows.subprocess.run", fake_run)
    b = WindowsBackend()
    assert b.ping_reachable("10.0.0.1", timeout_sec=2.0) is True
    assert called["args"] == ["ping", "-n", "1", "-w", "2000", "10.0.0.1"]
    assert "creationflags" in called["kwargs"]


def test_darwin_ping_reachable_invokes_ping(monkeypatch):
    called: dict = {}

    def fake_run(args, **kwargs):
        called["args"] = args
        return MagicMock(returncode=0)

    monkeypatch.setattr("vpn_daemon.platforms.darwin.subprocess.run", fake_run)
    b = DarwinBackend()
    assert b.ping_reachable("10.0.0.1", timeout_sec=1.5) is True
    assert called["args"] == ["ping", "-c", "1", "-W", "1500", "10.0.0.1"]


def test_linux_ping_reachable_invokes_ping(monkeypatch):
    called: dict = {}

    def fake_run(args, **kwargs):
        called["args"] = args
        return MagicMock(returncode=0)

    monkeypatch.setattr("vpn_daemon.platforms.linux.subprocess.run", fake_run)
    b = LinuxBackend()
    assert b.ping_reachable("10.0.0.1", timeout_sec=2.0) is True
    assert called["args"] == ["ping", "-c", "1", "-W", "2", "10.0.0.1"]


def test_windows_credentials_message_contains_credential_manager():
    assert "Windows Credential Manager" in WindowsBackend().credentials_missing_config_message()


def test_openvpn_popen_kwargs_windows_has_creationflags():
    kw = WindowsBackend().openvpn_popen_kwargs()
    assert "creationflags" in kw


def test_openvpn_popen_kwargs_unix_empty():
    assert DarwinBackend().openvpn_popen_kwargs() == {}
    assert LinuxBackend().openvpn_popen_kwargs() == {}
