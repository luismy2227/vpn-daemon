from __future__ import annotations

import logging
import sys

from vpn_daemon.platforms.base import PlatformBackend

log = logging.getLogger(__name__)


def get_platform_backend() -> PlatformBackend:
    """Return the strategy implementation for the current OS."""
    plat = sys.platform
    if plat == "win32":
        from vpn_daemon.platforms.windows import WindowsBackend

        return WindowsBackend()
    if plat == "darwin":
        from vpn_daemon.platforms.darwin import DarwinBackend

        return DarwinBackend()
    if plat.startswith("linux"):
        from vpn_daemon.platforms.linux import LinuxBackend

        return LinuxBackend()

    log.warning("Unknown sys.platform %r; using Linux-like backend.", plat)
    from vpn_daemon.platforms.linux import LinuxBackend

    return LinuxBackend()


__all__ = ["PlatformBackend", "get_platform_backend"]
