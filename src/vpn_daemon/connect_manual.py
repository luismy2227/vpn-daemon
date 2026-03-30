"""Print or run the same OpenVPN command line as the tray app (pin+TOTP auth file)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from vpn_daemon.config import load_config
from vpn_daemon.openvpn import build_openvpn_argv_and_files


def main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "Load config, build pin+TOTP auth-user-pass file, and print the exact "
            "OpenVPN argv (same as vpn_daemon tray). Use for manual testing."
        )
    )
    p.add_argument(
        "--config",
        type=Path,
        default=None,
        help="config.json path (default: VPN_DAEMON_CONFIG or config/config.json)",
    )
    p.add_argument(
        "--run",
        action="store_true",
        help="Run OpenVPN in the foreground with console output instead of only printing.",
    )
    ns = p.parse_args()

    cfg = load_config(ns.config)
    argv, auth_path, profile_tmp = build_openvpn_argv_and_files(cfg)
    print(subprocess.list2cmdline(argv))
    print(f"# --auth-user-pass file: {auth_path}")
    if profile_tmp is not None:
        print(f"# temp profile (management stripped): {profile_tmp}")
    else:
        print(f"# profile: {cfg.profile}")

    if ns.run:
        print("# Running OpenVPN (Ctrl+C to stop)…", file=sys.stderr)
        try:
            return int(subprocess.call(argv))
        finally:
            auth_path.unlink(missing_ok=True)
            if profile_tmp is not None:
                profile_tmp.unlink(missing_ok=True)

    print(
        "# Paste the first line into cmd.exe, or: .\\scripts\\connect.ps1 -Run",
        file=sys.stderr,
    )
    print(
        "# Keep temp files until OpenVPN exits; delete them afterward if still present.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
