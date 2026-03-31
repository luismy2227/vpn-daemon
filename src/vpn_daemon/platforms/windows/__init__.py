from __future__ import annotations

import ctypes
import subprocess
import sys
from typing import Any, Literal


class WindowsBackend:
    def ensure_elevated_or_relaunch(self) -> None:
        if ctypes.windll.shell32.IsUserAnAdmin():
            return
        params = " ".join(f'"{a}"' for a in sys.argv)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit(0)

    def openvpn_popen_kwargs(self) -> dict[str, Any]:
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}

    def ping_reachable(self, host: str, *, timeout_sec: float = 2.0) -> bool:
        ms = max(1, int(timeout_sec * 1000))
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            r = subprocess.run(
                ["ping", "-n", "1", "-w", str(ms), host],
                capture_output=True,
                text=True,
                timeout=max(5.0, timeout_sec + 3.0),
                creationflags=creationflags,
            )
            return r.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    def default_openvpn_path_guess(self) -> str:
        return r"C:\Program Files\OpenVPN\bin\openvpn.exe"

    def openvpn_executable_filetypes(self) -> list[tuple[str, str]]:
        return [("Executable", "*.exe"), ("All files", "*.*")]

    def credential_store_ui_label(self) -> str:
        return "Windows Credential Manager"

    def credentials_missing_config_message(self) -> str:
        return (
            "Credentials not found in config.json or Windows Credential Manager. "
            "Run the setup wizard to configure them."
        )

    def ui_font(self, spec: Literal["body", "bold"]) -> tuple[Any, ...] | None:
        if spec == "bold":
            return ("Segoe UI", 9, "bold")
        return ("Segoe UI", 9)
