from __future__ import annotations

import logging
import queue
import sys
import threading
from collections.abc import Callable
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from vpn_daemon.config import Config
from vpn_daemon.openvpn import VpnLinkState

log = logging.getLogger(__name__)

_TRAY = 32

# State → (R, G, B, A) dot colour
_STATE_COLOUR: dict[VpnLinkState, tuple[int, int, int, int]] = {
    VpnLinkState.CONNECTED:    (50,  210,  80, 255),   # green
    VpnLinkState.CONNECTING:   (230, 180,   0, 255),   # amber
    VpnLinkState.RECONNECTING: (230, 140,   0, 255),   # orange-amber
    VpnLinkState.EXITING:      (220, 110,  30, 255),   # orange
}
_DEFAULT_COLOUR: tuple[int, int, int, int] = (210, 55, 55, 255)  # red (disconnected/unknown)


def _resource_path(relative: str) -> Path:
    """Locate a bundled resource whether running from source or as a PyInstaller exe."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / relative
    # Running from source: walk up from this file to the project root
    return Path(__file__).resolve().parents[2] / relative


def _load_base_icon() -> Image.Image | None:
    """Load img/vpn.ico. Returns None if the file is absent (falls back to plain circles)."""
    path = _resource_path("img/vpn.ico")
    try:
        img = Image.open(path)
        # .ico files can have multiple sizes; pick the best fit for _TRAY
        img = img.convert("RGBA").resize((_TRAY, _TRAY), Image.LANCZOS)
        return img
    except Exception as e:
        log.debug("Could not load base icon %s: %s", path, e)
        return None


def _composite_icon(base: Image.Image, state: VpnLinkState) -> Image.Image:
    """Overlay a small status dot on the bottom-right corner of *base*."""
    colour = _STATE_COLOUR.get(state, _DEFAULT_COLOUR)
    img = base.copy()
    draw = ImageDraw.Draw(img)
    dot = max(6, _TRAY // 5)          # dot diameter ≈ 6–7 px at 32 px icon
    margin = 1
    x0 = _TRAY - dot - margin
    y0 = _TRAY - dot - margin
    # White halo for contrast against any background
    draw.ellipse((x0 - 1, y0 - 1, x0 + dot + 1, y0 + dot + 1), fill=(255, 255, 255, 220))
    draw.ellipse((x0, y0, x0 + dot, y0 + dot), fill=colour)
    return img


def _plain_icon(state: VpnLinkState) -> Image.Image:
    """Fallback: plain coloured circle when no base icon is available."""
    colour = _STATE_COLOUR.get(state, _DEFAULT_COLOUR)
    img = Image.new("RGBA", (_TRAY, _TRAY), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = max(1, _TRAY // 8)
    draw.ellipse((margin, margin, _TRAY - margin, _TRAY - margin), fill=colour)
    return img


# Module-level base icon, loaded once
_BASE_ICON: Image.Image | None = _load_base_icon()


def icon_for_state(state: VpnLinkState) -> Image.Image:
    if _BASE_ICON is not None:
        return _composite_icon(_BASE_ICON, state)
    return _plain_icon(state)


class TrayController:
    def __init__(self, config: Config, ctrl: queue.Queue[str]) -> None:
        self._config = config
        self._ctrl = ctrl
        self._icon: pystray.Icon | None = None

    def _maybe_notify(self, title: str, msg: str) -> None:
        if not self._config.notify_on_action:
            return
        icon = self._icon
        if not icon:
            return
        try:
            icon.notify(msg, title=title)
        except Exception as e:
            log.debug("notify: %s", e)

    def notify_state_change(self, prev: VpnLinkState, new: VpnLinkState) -> None:
        if new == VpnLinkState.CONNECTED:
            self._maybe_notify("VPN", "VPN Connected")
        elif prev == VpnLinkState.CONNECTED and new == VpnLinkState.DISCONNECTED:
            self._maybe_notify("VPN", "VPN Disconnected")
        elif prev == VpnLinkState.CONNECTED and new in (VpnLinkState.CONNECTING, VpnLinkState.RECONNECTING):
            self._maybe_notify("VPN", "VPN Reconnecting\u2026")
        elif prev in (VpnLinkState.CONNECTING, VpnLinkState.RECONNECTING) and new == VpnLinkState.DISCONNECTED:
            self._maybe_notify("VPN", "VPN Connection Failed")

    def _on_toggle(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._ctrl.put("toggle")

    def _on_connect(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._ctrl.put("connect")
        self._maybe_notify("VPN", "Starting OpenVPN\u2026")

    def _on_disconnect(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._ctrl.put("disconnect")
        self._maybe_notify("VPN", "Stopping OpenVPN\u2026")

    def _on_reconnect(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._ctrl.put("reconnect")
        self._maybe_notify("VPN", "Reconnecting OpenVPN\u2026")

    def _on_settings(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._ctrl.put("settings")

    def _on_quit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._ctrl.put("quit")

    def _menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("Toggle VPN", self._on_toggle, default=True, visible=False),
            pystray.MenuItem("OpenVPN + TOTP (tray)", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Connect", self._on_connect),
            pystray.MenuItem("Disconnect", self._on_disconnect),
            pystray.MenuItem("Reconnect", self._on_reconnect),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings", self._on_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._on_quit),
        )

    def run(self, after_visible: Callable[[pystray.Icon], None] | None = None) -> None:
        self._icon = pystray.Icon(
            "vpn_daemon",
            icon_for_state(VpnLinkState.DISCONNECTED),
            self._config.tray_tooltip[:120],
            menu=self._menu(),
        )

        def setup(icon: pystray.Icon) -> None:
            icon.visible = True
            if after_visible:
                threading.Thread(target=lambda: after_visible(icon), daemon=True).start()

        self._icon.run(setup=setup)

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()
