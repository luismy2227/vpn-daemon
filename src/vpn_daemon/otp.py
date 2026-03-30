"""TOTP + static PIN/password for OpenVPN auth-user-pass."""

from __future__ import annotations

import argparse

import pyotp


def build_otp_password(static_password: str, totp_secret: str) -> str:
    """Return ``static_password`` concatenated with the current TOTP code."""
    totp = pyotp.TOTP(totp_secret)
    return static_password + totp.now()


def main() -> int:
    p = argparse.ArgumentParser(description="Print pin+TOTP once (same as the VPN app uses).")
    p.add_argument("--pin", default="", help="Static PIN/password (may be empty)")
    p.add_argument("--secret", required=True, help="Base32 TOTP secret")
    p.add_argument("--code-only", action="store_true", help="Print only the 6-digit code")
    args = p.parse_args()
    if args.code_only:
        print(pyotp.TOTP(args.secret).now())
    else:
        print(build_otp_password(args.pin, args.secret))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
