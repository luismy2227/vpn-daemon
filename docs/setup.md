# Setup

## Prerequisites

- Windows 10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [OpenVPN Community](https://openvpn.net/community/) (`openvpn.exe`)
- `.ovpn` profile (e.g. from Pritunl) next to `config.json` or path in config

## Install

```powershell
.\scripts\install.ps1
```

Or: `uv sync`

## Configuration

1. Copy [`config/config.example.json`](../config/config.example.json) to `config/config.json`.
2. Set `username`, `password` (PIN/static part), `totp_secret` (Base32).
3. Set `openvpn_path` and `profile` (relative paths are resolved from the `config.json` directory).
4. Optional: `log_directory` for OpenVPN’s own log file.

Env: `VPN_DAEMON_CONFIG` = full path to `config.json` if not using the default location.

## Run

```powershell
.\scripts\run.ps1
```

Or: `uv run python -m vpn_daemon`

**Tray:** right-click **Connect** / **Disconnect** / **Reconnect** / **Quit**. The icon color follows OpenVPN management state (green when connected).

## TOTP check (compare with your VPN client)

```powershell
uv run python src/helper/otp.py --secret YOUR_BASE32 --pin yourpin
```

## QR → TOTP secret

```powershell
uv sync --extra helper
uv run --extra helper python src/helper/scan_totp_qr.py path\to\qr.png
```

## Logon task

See [task-scheduler.md](task-scheduler.md).
