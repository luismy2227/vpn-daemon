from __future__ import annotations

import logging
import subprocess
from typing import Callable

log = logging.getLogger(__name__)

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Exclude virtual/VPN adapters from the Ethernet fallback signature (they appear/disappear with VPN).
_PS_FILTER = r"""
$p = Get-NetConnectionProfile -ErrorAction SilentlyContinue |
  Where-Object {
    $a = $_.InterfaceAlias
    $a -notmatch '(?i)(vpn|tap|wintun|\btun\b|tun0|ppp|pritunl|openvpn|wireguard|zerotier|nordlynx|vEthernet|virtualbox|anyconnect|forticlient|globalprotect|juniper|pulse|sophos|checkpoint|citrix|netskope|zscaler|tailscale|nordvpn|expressvpn)'
  } |
  Sort-Object InterfaceAlias
if ($null -eq $p) { '' } else {
  ($p | ForEach-Object { $_.InterfaceAlias + '|' + $_.Name + '|' + [string]$_.IPv4Connectivity }) -join ';'
}
"""


def _wifi_uplink_signature() -> str | None:
    """If connected to Wi‑Fi, return wlan:<ssid> (stable when OpenVPN adds a virtual NIC)."""
    try:
        r = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=_CREATE_NO_WINDOW,
        )
        text = r.stdout or ""
    except (subprocess.TimeoutExpired, OSError) as e:
        log.debug("netsh wlan failed: %s", e)
        return None

    low = text.lower()
    if "there is no wireless interface" in low or "no wireless" in low:
        return None

    state = ""
    ssid = ""
    for line in text.splitlines():
        line = line.strip()
        l = line.lower()
        if l.startswith("state") and ":" in line:
            state = line.split(":", 1)[1].strip().lower()
        elif l.startswith("ssid") and "bssid" not in l and ":" in line:
            ssid = line.split(":", 1)[1].strip()

    if "connected" in state and ssid and ssid.lower() not in ("", "none", "off", "n/a"):
        return f"wlan:{ssid}"
    if "connected" in state:
        return "wlan:connected_no_ssid"
    if state:
        return f"wlan:state:{state.split()[0] if state else 'unknown'}"
    return None


def _physical_nic_signature() -> str:
    """Signature from non‑VPN connection profiles (Ethernet, etc.)."""
    try:
        r = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                _PS_FILTER.strip().replace("\n", " "),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=_CREATE_NO_WINDOW,
        )
        return (r.stdout or "").strip()
    except (subprocess.TimeoutExpired, OSError) as e:
        log.debug("filtered Get-NetConnectionProfile failed: %s", e)
        return ""


def get_network_signature() -> str:
    """Return a string that changes when the physical uplink (Wi‑Fi SSID or LAN profile) changes."""
    wifi = _wifi_uplink_signature()
    if wifi is not None:
        return wifi
    phys = _physical_nic_signature()
    if phys:
        return f"eth:{phys}"
    return ""


class NetworkChangePoller:
    def __init__(
        self,
        interval_seconds: float,
        debounce_seconds: float,
        on_change: Callable[[], None],
    ) -> None:
        self.interval_seconds = interval_seconds
        self.debounce_seconds = debounce_seconds
        self.on_change = on_change
        self._last: str | None = None
        self._pending_ticks = 0

    def tick(self) -> None:
        sig = get_network_signature()
        if self._last is None:
            self._last = sig
            return
        if sig != self._last:
            self._last = sig
            self._pending_ticks = int(self.debounce_seconds / max(self.interval_seconds, 0.1)) + 1
            log.info("Network signature changed, debouncing reconnect")
            return
        if self._pending_ticks > 0:
            self._pending_ticks -= 1
            if self._pending_ticks == 0:
                self.on_change()
