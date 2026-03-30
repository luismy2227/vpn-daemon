# vpn-daemon

Work-hours OpenVPN helper for Windows: system tray UI, TOTP-backed auth, reconnect on network change, and optional Task Scheduler logon.

## Documentation

- [Setup](docs/setup.md)
- [Configuration](docs/configuration.md)
- [Task Scheduler](docs/task-scheduler.md)
- [Troubleshooting](docs/troubleshooting.md)

## Quick start

```powershell
.\scripts\install.ps1
# Copy config\config.example.json to config\config.json and add profile.ovpn
.\scripts\run.ps1
```
