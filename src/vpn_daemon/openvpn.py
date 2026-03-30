from __future__ import annotations

import logging
import re
import socket
import subprocess
import tempfile
import time
from enum import Enum
from pathlib import Path

from vpn_daemon.config import Config
from vpn_daemon.otp import build_otp_password

log = logging.getLogger(__name__)


class VpnLinkState(str, Enum):
    UNKNOWN = "unknown"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    EXITING = "exiting"


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


_STATE_LINE = re.compile(rb"(?:>STATE:)?(\d{8,12}),([^,\r\n]+)")


def strip_embedded_management_directives(profile_text: str) -> tuple[str, int]:
    out: list[str] = []
    removed = 0
    for line in profile_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            out.append(line)
            continue
        first = stripped.split(None, 1)[0].lower()
        if first == "management":
            removed += 1
            continue
        out.append(line)
    trailing_nl = profile_text.endswith("\n") or profile_text.endswith("\r\n")
    text = "\n".join(out)
    if trailing_nl and text and not text.endswith("\n"):
        text += "\n"
    return text, removed


def build_openvpn_argv_and_files(cfg: Config) -> tuple[list[str], Path, Path | None]:
    """Build the same argv and temp files as :meth:`OpenVpnRunner.start`.

    Returns ``(argv, auth_path, profile_tmp)``. ``profile_tmp`` is set only when
    ``strip_profile_management`` removed embedded ``management`` lines and a temp
    profile was written. Caller must keep those paths until OpenVPN exits, then
    may delete them.
    """
    if not cfg.openvpn_path.is_file():
        raise FileNotFoundError(f"openvpn not found: {cfg.openvpn_path}")
    if not cfg.profile.is_file():
        raise FileNotFoundError(f"profile not found: {cfg.profile}")

    profile_tmp: Path | None = None
    auth_path: Path | None = None
    profile_arg = cfg.profile
    try:
        if cfg.strip_profile_management:
            text = cfg.profile.read_text(encoding="utf-8", errors="replace")
            new_text, n = strip_embedded_management_directives(text)
            if n > 0:
                if cfg.use_management:
                    log.info(
                        "Removed %s embedded 'management' line(s); using --management %s:%s",
                        n,
                        cfg.management_host,
                        cfg.management_port,
                    )
                else:
                    log.info(
                        "Removed %s embedded 'management' line(s); "
                        "OpenVPN runs without --management (use_management is false)",
                        n,
                    )
                fd, tmp_path = tempfile.mkstemp(
                    prefix="vpn-daemon-profile-", suffix=".ovpn", text=True
                )
                profile_tmp = Path(tmp_path)
                try:
                    with open(fd, "w", encoding="utf-8", newline="\n") as f:
                        f.write(new_text)
                except OSError:
                    profile_tmp.unlink(missing_ok=True)
                    raise
                profile_arg = profile_tmp

        otp_pw = build_otp_password(cfg.password, cfg.totp_secret)
        fd, auth_path_str = tempfile.mkstemp(prefix="vpn-daemon-auth-", suffix=".txt", text=True)
        auth_path = Path(auth_path_str)
        try:
            with open(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(cfg.username + "\n")
                f.write(otp_pw + "\n")
        except OSError:
            auth_path.unlink(missing_ok=True)
            if profile_tmp is not None:
                profile_tmp.unlink(missing_ok=True)
            raise

        args: list[str] = [
            str(cfg.openvpn_path),
            "--config",
            str(profile_arg),
            "--auth-user-pass",
            str(auth_path),
        ]
        if cfg.use_management:
            args.extend(
                [
                    "--management",
                    cfg.management_host,
                    str(cfg.management_port),
                ]
            )
        if cfg.log_directory:
            cfg.log_directory.mkdir(parents=True, exist_ok=True)
            log_file = cfg.log_directory / "openvpn.log"
            args.extend(["--log-append", str(log_file)])

        return args, auth_path, profile_tmp
    except OSError:
        if auth_path is not None:
            auth_path.unlink(missing_ok=True)
        if profile_tmp is not None:
            profile_tmp.unlink(missing_ok=True)
        raise


class OpenVpnRunner:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._proc: subprocess.Popen[str] | None = None
        self._auth_path: Path | None = None
        self._profile_tmp: Path | None = None
        self._last_mgmt_warn = 0.0

    def is_process_alive(self) -> bool:
        if self._proc is None:
            return False
        return self._proc.poll() is None

    def start(self) -> None:
        if self.is_process_alive():
            return

        cfg = self._config
        self._clear_profile_tmp()
        if self._auth_path is not None:
            try:
                self._auth_path.unlink(missing_ok=True)
            except OSError:
                pass
            self._auth_path = None

        args, auth_path, profile_tmp = build_openvpn_argv_and_files(cfg)
        self._auth_path = auth_path
        self._profile_tmp = profile_tmp

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            self._proc = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
                text=True,
            )
        except OSError:
            self._auth_path.unlink(missing_ok=True)
            self._auth_path = None
            self._clear_profile_tmp()
            raise

        log.info(
            "OpenVPN started pid=%s%s",
            self._proc.pid,
            "" if cfg.use_management else " (no management socket)",
        )

    def _clear_profile_tmp(self) -> None:
        if self._profile_tmp is not None:
            try:
                self._profile_tmp.unlink(missing_ok=True)
            except OSError:
                pass
            self._profile_tmp = None

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
        self._clear_profile_tmp()
        log.info("OpenVPN stopped")

    def query_management_state(self) -> VpnLinkState | None:
        if not self._config.use_management:
            return None
        host = self._config.management_host
        port = self._config.management_port
        buf = b""
        try:
            with socket.create_connection((host, port), timeout=3.0) as s:
                s.settimeout(0.5)
                try:
                    while True:
                        chunk = s.recv(8192)
                        if not chunk:
                            break
                        buf += chunk
                except TimeoutError:
                    pass

                if self._config.management_hold_release:
                    s.settimeout(3.0)
                    s.sendall(b"hold release\n")
                    s.settimeout(0.5)
                    try:
                        while True:
                            chunk = s.recv(8192)
                            if not chunk:
                                break
                            buf += chunk
                    except TimeoutError:
                        pass

                s.settimeout(3.0)
                s.sendall(b"state\n")
                s.settimeout(0.75)
                for _ in range(40):
                    try:
                        chunk = s.recv(4096)
                    except TimeoutError:
                        break
                    if not chunk:
                        break
                    buf += chunk
                    if _STATE_LINE.search(buf):
                        break
        except OSError as e:
            log.debug("management connect failed: %s", e)
            return None

        matches = list(_STATE_LINE.finditer(buf))
        if not matches:
            log.debug("management: no >STATE in: %r", buf[:500])
            return None
        raw = matches[-1].group(2).decode("utf-8", errors="replace").strip()
        return _map_ov_state(raw)

    def effective_link_state(self) -> VpnLinkState:
        alive = self.is_process_alive()
        cfg = self._config

        if alive and not cfg.use_management:
            host = cfg.internal_ping_host
            if host:
                return (
                    VpnLinkState.CONNECTED
                    if _ping_host(host)
                    else VpnLinkState.CONNECTING
                )
            return VpnLinkState.CONNECTED

        mgmt = self.query_management_state()

        if alive and mgmt is not None:
            if mgmt == VpnLinkState.CONNECTED:
                host = self._config.internal_ping_host
                if host and not _ping_host(host):
                    return VpnLinkState.CONNECTING
            return mgmt

        if alive and mgmt is None:
            now = time.monotonic()
            if cfg.use_management and now - self._last_mgmt_warn > 45.0:
                self._last_mgmt_warn = now
                log.warning(
                    "OpenVPN running but management on %s:%s is not usable. "
                    "Check strip_profile_management and management_port.",
                    cfg.management_host,
                    cfg.management_port,
                )
            if cfg.internal_ping_host and _ping_host(cfg.internal_ping_host):
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
