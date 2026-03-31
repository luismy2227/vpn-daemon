from __future__ import annotations

from typing import Any, Literal, Protocol


class PlatformBackend(Protocol):
    """OS-specific behavior for elevation, subprocess, ping, and setup UI."""

    def ensure_elevated_or_relaunch(self) -> None:
        """Windows: re-exec with admin if needed. Unix: typically no-op."""
        ...

    def openvpn_popen_kwargs(self) -> dict[str, Any]:
        """Extra keyword arguments for subprocess.Popen when launching OpenVPN."""
        ...

    def ping_reachable(self, host: str, *, timeout_sec: float = 2.0) -> bool:
        """Return True if *host* responds to one ICMP echo (platform-specific ping)."""
        ...

    def default_openvpn_path_guess(self) -> str:
        """Suggested OpenVPN binary path when config has none."""
        ...

    def openvpn_executable_filetypes(self) -> list[tuple[str, str]]:
        """Tk filedialog filetypes for picking the OpenVPN binary."""
        ...

    def credential_store_ui_label(self) -> str:
        """Short label for the credential backend in the setup wizard."""
        ...

    def credentials_missing_config_message(self) -> str:
        """Sentence fragment for CredentialsMissingError (after generic intro)."""
        ...

    def ui_font(self, spec: Literal["body", "bold"]) -> tuple[Any, ...] | None:
        """Tk font tuple, or None to use Tk defaults."""
        ...
