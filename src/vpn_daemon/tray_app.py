from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass, field

import pystray
from PIL import Image, ImageDraw

from vpn_daemon.openvpn import VpnLinkState
from vpn_daemon.state import RuntimeState

log = logging.getLogger(__name__)


@dataclass
class UiState:
    """Read by tray menu lambdas; written by daemon thread."""

    link: VpnLinkState = VpnLinkState.UNKNOWN
    paused: bool = False
    user_disconnected: bool = False
    within_hours: bool = True
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def status_label(self) -> str:
        with self._lock:
            if self.paused:
                base = "Paused"
            elif self.user_disconnected:
                base = "Disconnected (manual)"
            elif self.link == VpnLinkState.CONNECTED:
                base = "Connected"
            elif self.link in (VpnLinkState.CONNECTING, VpnLinkState.RECONNECTING):
                base = "Connecting…"
            elif self.link == VpnLinkState.EXITING:
                base = "Exiting…"
            else:
                base = "Disconnected"
            if not self.within_hours and not self.paused:
                base += " (outside work hours)"
            return base

    def set_link(self, link: VpnLinkState) -> None:
        with self._lock:
            self.link = link

    def set_flags(self, *, paused: bool | None = None, within_hours: bool | None = None) -> None:
        with self._lock:
            if paused is not None:
                self.paused = paused
            if within_hours is not None:
                self.within_hours = within_hours

    def set_user_disconnected(self, v: bool) -> None:
        with self._lock:
            self.user_disconnected = v

    def is_paused(self) -> bool:
        with self._lock:
            return self.paused

    def user_wants_disconnected(self) -> bool:
        with self._lock:
            return self.user_disconnected

    def pause_menu_label(self) -> str:
        with self._lock:
            return "Resume daemon" if self.paused else "Pause daemon"

    def snapshot_persist(self) -> RuntimeState:
        with self._lock:
            return RuntimeState(daemon_paused=self.paused, user_disconnected=self.user_disconnected)

    def toggle_pause(self) -> None:
        with self._lock:
            self.paused = not self.paused


def _circle_icon(size: int, fill: tuple[int, int, int, int]) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = max(2, size // 8)
    draw.ellipse((margin, margin, size - margin, size - margin), fill=fill)
    return img


def icon_image_for_state(ui: UiState) -> Image.Image:
    with ui._lock:
        paused = ui.paused
        disc = ui.user_disconnected
        link = ui.link
    size = 64
    if paused:
        return _circle_icon(size, (128, 128, 128, 255))
    if disc or link == VpnLinkState.DISCONNECTED:
        return _circle_icon(size, (200, 60, 60, 255))
    if link == VpnLinkState.CONNECTED:
        return _circle_icon(size, (60, 180, 90, 255))
    return _circle_icon(size, (200, 160, 60, 255))


class TrayController:
    def __init__(self, ctrl: queue.Queue, ui: UiState) -> None:
        self._ctrl = ctrl
        self._ui = ui
        self._icon: pystray.Icon | None = None
        self._stop = threading.Event()

    def _menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(lambda item: self._ui.status_label(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda item: self._ui.pause_menu_label(),
                self._on_toggle_pause,
            ),
            pystray.MenuItem("Reconnect", self._on_reconnect),
            pystray.MenuItem("Disconnect", self._on_disconnect),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._on_quit),
        )

    def _on_toggle_pause(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._ctrl.put("toggle_pause")

    def _on_reconnect(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._ctrl.put("reconnect")

    def _on_disconnect(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._ctrl.put("disconnect")

    def _on_quit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._ctrl.put("quit")

    def _refresh_loop(self) -> None:
        while not self._stop.wait(timeout=2.0):
            try:
                if self._icon:
                    self._icon.icon = icon_image_for_state(self._ui)
                    self._icon.update_menu()
            except Exception as e:
                log.debug("tray refresh: %s", e)

    def run(self) -> None:
        image = icon_image_for_state(self._ui)
        self._icon = pystray.Icon(
            "vpn_daemon",
            image,
            "VPN daemon",
            menu=self._menu(),
        )
        t = threading.Thread(target=self._refresh_loop, daemon=True)
        t.start()
        self._icon.run()

    def stop(self) -> None:
        self._stop.set()
        if self._icon:
            self._icon.stop()
