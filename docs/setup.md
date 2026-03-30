# Setup

## Prerequisites

- Windows 10 or later
- [uv](https://docs.astral.sh/uv/getting-started/installation/) on your PATH
- OpenVPN installed (Community installer is typical), or another build whose `openvpn.exe` path you put in config
- A Pritunl-exported profile (`.ovpn` or `.conf`) and your account password plus TOTP secret

## Install

From the repository root:

```powershell
.\scripts\install.ps1
```

Or manually:

```powershell
uv sync
```

## Configuration

1. Copy [`config/config.example.json`](../config/config.example.json) to `config/config.json`.
2. Fill in `username`, `password`, and `totp_secret`.

### TOTP secret from a QR screenshot (local, offline)

Install the optional helper dependency and run:

```powershell
uv sync --extra helper
uv run --extra helper python src/helper/scan_totp_qr.py path\to\your\qr-screenshot.png
```

It prints the Base32 `secret` for `totp_secret`. Use `--json` for issuer/label plus secret. Do not upload enrollment QRs to third-party sites; this runs only on your machine.
3. Set `openvpn_path` to your `openvpn.exe`.
4. Copy your VPN profile into `config/profile.ovpn` (or set `profile` to an absolute path). If the profile references external certificate files, keep those paths valid or embed certs in the profile.

The daemon adds `--management` on the command line so it can read link state. Ensure nothing else binds the same `management_port` (default `7505`).

## First run

```powershell
.\scripts\run.ps1
```

Or:

```powershell
uv run python -m vpn_daemon
```

Optional: set `VPN_DAEMON_CONFIG` to the full path of `config.json` if it lives elsewhere.

## Tray

After start you should see a tray icon:

- Green: connected
- Amber: connecting
- Red: disconnected (or you chose Disconnect)
- Gray: daemon paused

Use the menu for Pause, Reconnect, Disconnect, and Quit.

## State file

Pause and manual disconnect are stored under `%LOCALAPPDATA%\vpn-daemon\state.json` so they survive restarts.
