# Troubleshooting

## Config not found

Ensure `config/config.json` exists or set `VPN_DAEMON_CONFIG` to its full path. Run [`scripts/export.ps1`](../scripts/export.ps1) to see what the scripts resolve.

## OpenVPN fails to start

- Verify `openvpn_path` and `profile` with `export.ps1`.
- Run OpenVPN manually with the same profile to confirm credentials and certificates.
- If the profile uses relative paths to `.crt` / `.key` files, either keep those files next to the profile or use absolute paths inside the profile.

## Management / tray always “Connecting”

- Another process may be using `management_port`; change the port in `config.json` and restart.
- Firewall or policy might block the loopback management socket (uncommon).
- If the server profile forbids client-side management, you may need to rely on process-only detection; set `internal_ping_host` to an internal address to improve “connected” accuracy.

## TOTP failures

- Check system clock (TOTP is time-based).
- Confirm the secret is Base32 as expected by your VPN provider.

## Wi-Fi change does not reconnect

- Network detection uses `Get-NetConnectionProfile` and falls back to `netsh wlan show interfaces`. Corporate tools may block these; watch the log for errors.
- Pause or manual disconnect disables auto-reconnect until you Resume or Reconnect.

## Tray icon missing

- Some Windows builds hide tray icons in the overflow area; click “Show hidden icons”.
- Run from `run.ps1` or a logged-on session; services sessions do not show a per-user tray.

## Logs

- Application: console if started from a terminal; otherwise configure logging later as needed.
- OpenVPN: if `log_directory` is set, see `openvpn.log` in that folder.
