#!/usr/bin/env python3
"""
Decode a TOTP enrollment QR from a local image file (offline).

Requires optional deps: uv sync --extra helper

Usage:
  uv run --extra helper python src/helper/scan_totp_qr.py path/to/screenshot.png
  uv run --extra helper python src/helper/scan_totp_qr.py qr.png --json

The QR should contain an otpauth:// URI. This script never uploads the image.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from pathlib import Path


def _decode_qr_opencv(image_path: Path) -> str:
    import cv2  # type: ignore[import-untyped]

    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    detector = cv2.QRCodeDetector()
    data, _bbox, _straight = detector.detectAndDecode(img)
    if not data:
        raise ValueError("No QR code found in image (try a larger/clearer crop).")
    return data.strip()


_BASE32_RE = re.compile(r"^[A-Z2-7]+=*$", re.IGNORECASE)


def parse_otpauth_uri(uri: str) -> dict[str, str]:
    """Parse otpauth://totp/... or otpauth://hotp/... query for secret and metadata."""
    u = urllib.parse.urlparse(uri)
    if u.scheme != "otpauth":
        raise ValueError(f"Expected otpauth:// URI, got scheme={u.scheme!r}")
    if u.netloc.lower() not in ("totp", "hotp"):
        raise ValueError(f"Expected totp or hotp host, got {u.netloc!r}")

    qs = urllib.parse.parse_qs(u.query, strict_parsing=False)
    secret = (qs.get("secret") or [None])[0]
    if not secret:
        raise ValueError("No secret= in otpauth query string.")
    secret = secret.replace(" ", "").upper()
    if not _BASE32_RE.match(secret):
        raise ValueError("Secret does not look like Base32; check the QR content.")

    issuer = (qs.get("issuer") or [None])[0]
    label = urllib.parse.unquote(u.path.lstrip("/")) if u.path else ""

    return {
        "type": u.netloc.lower(),
        "secret": secret,
        "issuer": issuer or "",
        "label": label,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Extract TOTP secret from a local QR image.")
    p.add_argument("image", type=Path, help="Path to PNG/JPG (screenshot of enrollment QR)")
    p.add_argument(
        "--json",
        action="store_true",
        help="Print JSON (secret, issuer, label); omit human-readable secret line",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="With --json, print only JSON and no stderr warnings",
    )
    args = p.parse_args()

    if not args.quiet:
        print(
            "Keep the secret out of git; use config/config.json (gitignored). "
            "Delete the image if you no longer need it.",
            file=sys.stderr,
        )

    try:
        raw = _decode_qr_opencv(args.image.resolve())
    except ImportError:
        print(
            "Missing OpenCV. Install helper extra:  uv sync --extra helper",
            file=sys.stderr,
        )
        return 2
    except (OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1

    if raw.lower().startswith("otpauth://"):
        try:
            info = parse_otpauth_uri(raw)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1
        if info["type"] == "hotp" and not args.quiet:
            print(
                "Warning: This QR is HOTP; vpn-daemon uses TOTP only.",
                file=sys.stderr,
            )
        if args.json:
            print(json.dumps(info, indent=2))
        else:
            if (info.get("issuer") or info.get("label")) and not args.quiet:
                parts = [x for x in (info.get("issuer"), info.get("label")) if x]
                print(f"Decoded ({' — '.join(parts)})", file=sys.stderr)
            print(info["secret"])
        return 0

    print(
        "QR decoded but payload is not otpauth://. First 120 chars:\n"
        + raw[:120]
        + ("..." if len(raw) > 120 else ""),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
