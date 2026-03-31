from __future__ import annotations

import socket
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vpn_daemon.openvpn import (
    VpnLinkState,
    _STATE_LINE,
    _map_ov_state,
    strip_embedded_management_directives,
    OpenVpnRunner,
)
from vpn_daemon.config import Config


# ── strip_embedded_management_directives ──────────────────────────────────────

def test_strip_removes_management_line():
    text = "client\nmanagement 127.0.0.1 7505\ndev tun\n"
    out, n = strip_embedded_management_directives(text)
    assert n == 1
    assert "management 127.0.0.1" not in out
    assert "client" in out
    assert "dev tun" in out


def test_strip_keeps_management_hold():
    text = "client\nmanagement-hold\ndev tun\n"
    out, n = strip_embedded_management_directives(text)
    assert n == 0
    assert "management-hold" in out


def test_strip_preserves_trailing_newline():
    text = "client\nmanagement 127.0.0.1 7505\n"
    out, _ = strip_embedded_management_directives(text)
    assert out.endswith("\n")


def test_strip_preserves_comments():
    text = "# comment\nmanagement 127.0.0.1 7505\nclient\n"
    out, n = strip_embedded_management_directives(text)
    assert n == 1
    assert "# comment" in out


def test_strip_no_management_line():
    text = "client\ndev tun\n"
    out, n = strip_embedded_management_directives(text)
    assert n == 0
    assert out == text


# ── _map_ov_state ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name,expected", [
    ("CONNECTED", VpnLinkState.CONNECTED),
    ("connected", VpnLinkState.CONNECTED),
    ("WAIT", VpnLinkState.CONNECTING),
    ("AUTH", VpnLinkState.CONNECTING),
    ("GET_CONFIG", VpnLinkState.CONNECTING),
    ("ASSIGN_IP", VpnLinkState.CONNECTING),
    ("ADD_ROUTES", VpnLinkState.CONNECTING),
    ("RECONNECTING", VpnLinkState.CONNECTING),
    ("RESOLVE", VpnLinkState.CONNECTING),
    ("TCP_CONNECT", VpnLinkState.CONNECTING),
    ("EXITING", VpnLinkState.EXITING),
    ("BOGUS", VpnLinkState.UNKNOWN),
])
def test_map_ov_state(name, expected):
    assert _map_ov_state(name) == expected


# ── _STATE_LINE regex ─────────────────────────────────────────────────────────

def test_state_line_matches_command_response():
    buf = b"1617891234,CONNECTED,SUCCESS,10.0.0.2,192.168.1.1\r\nEND\r\n"
    m = _STATE_LINE.search(buf)
    assert m is not None
    assert m.group(2) == b"CONNECTED"


def test_state_line_matches_realtime_notification():
    buf = b">STATE:1617891234,CONNECTED,SUCCESS,10.0.0.2\r\n"
    m = _STATE_LINE.search(buf)
    assert m is not None
    assert m.group(2) == b"CONNECTED"


def test_state_line_does_not_match_banner():
    buf = b">INFO:OpenVPN Management Interface Version 3 -- type 'help' for more info\r\n"
    assert _STATE_LINE.search(buf) is None


def test_state_line_matches_connecting_state():
    buf = b"1617891234,AUTH,,\r\nEND\r\n"
    m = _STATE_LINE.search(buf)
    assert m is not None
    assert m.group(2) == b"AUTH"


# ── query_management_state ────────────────────────────────────────────────────

def _make_config(**kwargs) -> Config:
    defaults = dict(
        username="u", password="p", totp_secret="JBSWY3DPEHPK3PXP",
        openvpn_path=Path("openvpn.exe"), profile=Path("vpn.ovpn"),
        use_management=True, management_host="127.0.0.1", management_port=17505,
        strip_profile_management=False, management_hold_release=False,
    )
    defaults.update(kwargs)
    return Config(**defaults)


def _run_mock_mgmt_server(
    host: str, port: int, state_response: bytes, event: threading.Event
) -> None:
    """Simulate OpenVPN management: send banner, wait for 'state', reply."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(1)
    event.set()
    try:
        conn, _ = srv.accept()
        conn.settimeout(5.0)
        conn.sendall(b">INFO:OpenVPN Management Interface Version 3\r\n")
        buf = b""
        while b"state" not in buf:
            chunk = conn.recv(256)
            if not chunk:
                break
            buf += chunk
        conn.sendall(state_response)
        conn.close()
    finally:
        srv.close()


def test_query_management_state_connected():
    HOST, PORT = "127.0.0.1", 17505
    state_response = b"1617891234,CONNECTED,SUCCESS,10.0.0.2\r\nEND\r\n"
    ready = threading.Event()
    t = threading.Thread(
        target=_run_mock_mgmt_server,
        args=(HOST, PORT, state_response, ready),
        daemon=True,
    )
    t.start()
    ready.wait(timeout=2)

    runner = OpenVpnRunner(_make_config(management_port=PORT))
    state = runner.query_management_state()
    assert state == VpnLinkState.CONNECTED


def test_query_management_state_connecting():
    HOST, PORT = "127.0.0.1", 17506
    state_response = b"1617891234,AUTH,,\r\nEND\r\n"
    ready = threading.Event()
    t = threading.Thread(
        target=_run_mock_mgmt_server,
        args=(HOST, PORT, state_response, ready),
        daemon=True,
    )
    t.start()
    ready.wait(timeout=2)

    runner = OpenVpnRunner(_make_config(management_port=PORT))
    state = runner.query_management_state()
    assert state == VpnLinkState.CONNECTING


def test_query_management_state_unreachable():
    runner = OpenVpnRunner(_make_config(management_port=19999))
    state = runner.query_management_state()
    assert state is None


def test_query_management_state_disabled():
    runner = OpenVpnRunner(_make_config(use_management=False))
    assert runner.query_management_state() is None


# ── effective_link_state ──────────────────────────────────────────────────────

def test_effective_link_state_dead_process():
    runner = OpenVpnRunner(_make_config())
    # _proc is None → not alive → DISCONNECTED
    assert runner.effective_link_state() == VpnLinkState.DISCONNECTED


def test_effective_link_state_no_management_alive():
    cfg = _make_config(use_management=False)
    runner = OpenVpnRunner(cfg)
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None  # alive
    runner._proc = mock_proc
    assert runner.effective_link_state() == VpnLinkState.CONNECTED


def test_effective_link_state_management_returns_state():
    runner = OpenVpnRunner(_make_config())
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    runner._proc = mock_proc

    with patch.object(runner, "query_management_state", return_value=VpnLinkState.CONNECTING):
        assert runner.effective_link_state() == VpnLinkState.CONNECTING


def test_effective_link_state_management_none_falls_back_to_connecting():
    runner = OpenVpnRunner(_make_config())
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    runner._proc = mock_proc

    with patch.object(runner, "query_management_state", return_value=None):
        assert runner.effective_link_state() == VpnLinkState.CONNECTING
