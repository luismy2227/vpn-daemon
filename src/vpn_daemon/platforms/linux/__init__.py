from __future__ import annotations

import subprocess
from typing import Any, Literal


class LinuxBackend:
    def ensure_elevated_or_relaunch(self) -> None:
        return

    def openvpn_popen_kwargs(self) -> dict[str, Any]:
        return {}

    def ping_reachable(self, host: str, *, timeout_sec: float = 2.0) -> bool:
        # GNU inetutils/iputils: -W is timeout in seconds.
        w = max(1, int(timeout_sec)) if timeout_sec >= 1 else 1
        try:
            r = subprocess.run(
                ["ping", "-c", "1", "-W", str(w), host],
                capture_output=True,
                text=True,
                timeout=max(5.0, timeout_sec + 3.0),
            )
            return r.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    def default_openvpn_path_guess(self) -> str:
        return "/usr/sbin/openvpn"

    def openvpn_executable_filetypes(self) -> list[tuple[str, str]]:
        return [
            ("OpenVPN binary", "openvpn"),
            ("All files", "*"),
        ]

    def credential_store_ui_label(self) -> str:
        return "system secret store (keyring)"

    def credentials_missing_config_message(self) -> str:
        return (
            "Credentials not found in config.json or the system keyring. "
            "Run the setup wizard to configure them."
        )

    def ui_font(self, spec: Literal["body", "bold"]) -> tuple[Any, ...] | None:
        return None
