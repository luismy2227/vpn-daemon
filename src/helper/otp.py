#!/usr/bin/env python3
"""CLI wrapper; same TOTP logic as the app (requires: uv sync)."""

from __future__ import annotations

from vpn_daemon.otp import main

if __name__ == "__main__":
    raise SystemExit(main())
