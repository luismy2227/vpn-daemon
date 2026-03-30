# vpn-daemon v0.4.0

Windows **system tray** app that starts **OpenVPN** with **`username` + (PIN + TOTP)** authentication.

Menu: **Connect**, **Disconnect**, **Reconnect**, **Settings**, **Quit**.

## Quick start

```powershell
.\scripts\install.ps1
.\scripts\run.ps1        # or: uv run python -m vpn_daemon
```

On first launch, a UAC prompt requests administrator rights (required for routing), then the **setup wizard** opens to enter your credentials and paths. Credentials are stored in **Windows Credential Manager** — never in plain text on disk.

## Features

- TOTP + PIN authentication (PIN + 6-digit TOTP appended as one password string)
- Real-time tray icon: green (connected), yellow (connecting), red (disconnected)
- Balloon notifications on state changes (enable `notify_on_action` in settings)
- Settings UI accessible from tray menu — no manual JSON editing required
- OpenVPN management socket for accurate connection state
- Auto-start via Windows Task Scheduler

## Docs

- [Setup](docs/setup.md)
- [Configuration](docs/configuration.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Development & Building](docs/development.md)

## Helpers (`uv sync --extra helper`)

- [TOTP CLI](src/helper/otp.py) — `uv run python src/helper/otp.py --secret BASE32 --pin yourpin`
- [QR → secret](src/helper/scan_totp_qr.py) — `uv run --extra helper python src/helper/scan_totp_qr.py qr.png`
