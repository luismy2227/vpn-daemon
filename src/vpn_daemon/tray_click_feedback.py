from __future__ import annotations

import logging
import sys
from typing import Protocol

log = logging.getLogger(__name__)


class TrayClickFeedback(Protocol):
    def play(self) -> None:
        """Play short feedback when the tray icon receives a primary click."""


class NullTrayClickFeedback:
    """No-op implementation for platforms without audio feedback yet."""

    def play(self) -> None:
        return


class WindowsTrayClickFeedback:
    def play(self) -> None:
        try:
            import winsound

            winsound.MessageBeep(winsound.MB_OK)
        except Exception as e:
            log.debug("tray click sound: %s", e)


def get_tray_click_feedback() -> TrayClickFeedback:
    if sys.platform == "win32":
        return WindowsTrayClickFeedback()
    return NullTrayClickFeedback()
