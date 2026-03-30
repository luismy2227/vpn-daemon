from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


WDAY_MAP = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


@dataclass
class Config:
    username: str
    password: str
    totp_secret: str
    openvpn_path: Path
    profile: Path
    check_interval_seconds: float = 30.0
    management_host: str = "127.0.0.1"
    management_port: int = 7505
    timezone: str = "UTC"
    timezone_windows: str | None = None
    work_days: list[str] = field(default_factory=lambda: ["mon", "tue", "wed", "thu", "fri"])
    work_hours_start: str = "09:00"
    work_hours_end: str = "17:30"
    reconnect_outside_hours: bool = False
    network_poll_interval_seconds: float = 5.0
    network_reconnect_debounce_seconds: float = 3.0
    network_ignore_seconds_after_vpn_start: float = 60.0
    internal_ping_host: str | None = None
    log_directory: Path | None = None

    @property
    def work_weekdays(self) -> set[int]:
        return {WDAY_MAP[d.lower()[:3]] for d in self.work_days}


def _resolve_path(base: Path, p: str | Path) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path.resolve()
    return (base / path).resolve()


def default_config_path() -> Path:
    env = os.environ.get("VPN_DAEMON_CONFIG")
    if env:
        return Path(env).expanduser().resolve()
    root = Path(__file__).resolve().parents[2]
    return (root / "config" / "config.json").resolve()


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

    profile = _resolve_path(base, raw["profile"])
    openvpn = Path(raw["openvpn_path"]).expanduser()

    log_dir = raw.get("log_directory")
    log_path = Path(log_dir).expanduser().resolve() if log_dir else None

    return Config(
        username=str(raw["username"]),
        password=str(raw["password"]),
        totp_secret=str(raw["totp_secret"]),
        openvpn_path=openvpn,
        profile=profile,
        check_interval_seconds=float(raw.get("check_interval_seconds", 30)),
        management_host=str(raw.get("management_host", "127.0.0.1")),
        management_port=int(raw.get("management_port", 7505)),
        timezone=str(raw.get("timezone", "UTC")),
        timezone_windows=(
            str(raw["timezone_windows"]).strip()
            if raw.get("timezone_windows")
            else None
        ),
        work_days=list(raw.get("work_days", ["mon", "tue", "wed", "thu", "fri"])),
        work_hours_start=str(raw.get("work_hours_start", "09:00")),
        work_hours_end=str(raw.get("work_hours_end", "17:30")),
        reconnect_outside_hours=bool(raw.get("reconnect_outside_hours", False)),
        network_poll_interval_seconds=float(raw.get("network_poll_interval_seconds", 5)),
        network_reconnect_debounce_seconds=float(raw.get("network_reconnect_debounce_seconds", 3)),
        network_ignore_seconds_after_vpn_start=float(
            raw.get("network_ignore_seconds_after_vpn_start", 60)
        ),
        internal_ping_host=raw.get("internal_ping_host"),
        log_directory=log_path,
    )


def default_state_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    d = Path(base) / "vpn-daemon"
    d.mkdir(parents=True, exist_ok=True)
    return d
