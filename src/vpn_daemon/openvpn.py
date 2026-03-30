from __future__ import annotations

import logging
import re
import socket
import subprocess
import tempfile
from enum import Enum
from pathlib import Path

import pyotp

from vpn_daemon.config import Config

log = logging.getLogger(__name__)


class VpnLinkState(str, Enum):
    UNKNOWN = "unknown"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    EXITING = "exiting"


# OpenVPN management state names (subset we care about)
_CONNECTED_STATES = frozenset({"CONNECTED"})
_CONNECTING_STATES = frozenset(
    {
        "CONNECTING",
        "WAIT",
        "AUTH",
        "GET_CONFIG",
        "ASSIGN_IP",
        "ADD_ROUTES",
        "RECONNECTING",
        "RESOLVE",
        "TCP_CONNECT",
    }
)
_EXITING_STATES = frozenset({"EXITING"})


def _map_ov_state(name: str) -> VpnLinkState:
    u = name.upper()
    if u in _CONNECTED_STATES:
        return VpnLinkState.CONNECTED
    if u in _EXITING_STATES:
        return VpnLinkState.EXITING
    if u in _CONNECTING_STATES:
        return VpnLinkState.CONNECTING
    return VpnLinkState.UNKNOWN


_STATE_LINE = re.compile(rb">STATE:(\d+),([^,]+),")


def build_otp_password(static_password: str, totp_secret: str) -> str:
    totp = pyotp.TOTP(totp_secret)
    return static_password + totp.now()


class OpenVpnRunner:
    """Starts and stops OpenVPN; queries management socket for link state."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._proc: subprocess.Popen[str] | None = None
        self._auth_path: Path | None = None

    @property
    def pid(self) -> int | None:
        if self._proc is None or self._proc.poll() is not None:
            return None
        return self._proc.pid

    def is_process_alive(self) -> bool:
        if self._proc is None:
            return False
        return self._proc.poll() is None

    def start(self) -> None:
        if self.is_process_alive():
            return

        cfg = self._config
        if not cfg.openvpn_path.is_file():
            raise FileNotFoundError(f"openvpn not found: {cfg.openvpn_path}")
        if not cfg.profile.is_file():
            raise FileNotFoundError(f"profile not found: {cfg.profile}")

        otp_pw = build_otp_password(cfg.password, cfg.totp_secret)
        fd, auth_path = tempfile.mkstemp(prefix="vpn-daemon-auth-", suffix=".txt", text=True)
        self._auth_path = Path(auth_path)
        try:
            with open(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(cfg.username + "\n")
                f.write(otp_pw + "\n")
        except OSError:
            self._auth_path.unlink(missing_ok=True)
            self._auth_path = None
            raise

        args: list[str] = [
            str(cfg.openvpn_path),
            "--config",
            str(cfg.profile),
            "--auth-user-pass",
            str(self._auth_path),
            "--management",
            cfg.management_host,
            str(cfg.management_port),
        ]
        if cfg.log_directory:
            cfg.log_directory.mkdir(parents=True, exist_ok=True)
            log_file = cfg.log_directory / "openvpn.log"
            args.extend(["--log-append", str(log_file)])

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        self._proc = subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            text=True,
        )
        log.info("OpenVPN started pid=%s", self._proc.pid)

    def stop(self) -> None:
        if self._proc is not None:
            try:
                if self._proc.poll() is None:
                    self._proc.terminate()
                    try:
                        self._proc.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        self._proc.kill()
            finally:
                self._proc = None
        if self._auth_path is not None:
            try:
                self._auth_path.unlink(missing_ok=True)
            except OSError:
                pass
            self._auth_path = None
        log.info("OpenVPN stopped")

    def query_management_state(self) -> VpnLinkState | None:
        """Return mapped state from management, or None if unreachable."""
        host = self._config.management_host
        port = self._config.management_port
        try:
            with socket.create_connection((host, port), timeout=2.0) as s:
                s.settimeout(2.0)
                # Drain banner until idle briefly, then query state
                s.settimeout(0.3)
                buf = b""
                try:
                    while True:
                        chunk = s.recv(2048)
                        if not chunk:
                            break
                        buf += chunk
                except TimeoutError:
                    pass
                s.settimeout(2.0)
                s.sendall(b"state\n")
                response = buf
                for _ in range(50):
                    chunk = s.recv(512)
                    if not chunk:
                        break
                    response += chunk
                    if _STATE_LINE.search(response):
                        break
        except OSError as e:
            log.debug("management connect failed: %s", e)
            return None

        m = _STATE_LINE.search(response)
        if not m:
            return None
        name = m.group(2).decode("ascii", errors="replace").strip()
        return _map_ov_state(name)

    def effective_link_state(self) -> VpnLinkState:
        """Process + management + optional ping."""
        alive = self.is_process_alive()
        mgmt = self.query_management_state()

        if alive and mgmt is not None:
            if mgmt == VpnLinkState.CONNECTED:
                host = self._config.internal_ping_host
                if host and not _ping_host(host):
                    return VpnLinkState.CONNECTING
            return mgmt

        if alive and mgmt is None:
            if self._config.internal_ping_host:
                if _ping_host(self._config.internal_ping_host):
                    return VpnLinkState.CONNECTED
            return VpnLinkState.CONNECTING

        return VpnLinkState.DISCONNECTED


def _ping_host(host: str) -> bool:
    try:
        r = subprocess.run(
            ["ping", "-n", "1", "-w", "2000", host],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False
