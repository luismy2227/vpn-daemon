# Configuration

## Credentials & paths

| Field | Description |
| --- | --- |
| `username` | OpenVPN username |
| `password` | PIN or static password (TOTP digits are appended automatically) |
| `totp_secret` | Base32 TOTP secret |
| `openvpn_path` | Full path to `openvpn.exe` |
| `profile` | `.ovpn` path (relative to the folder containing `config.json`, unless absolute) |

## OpenVPN management (tray status)

| Field | Default | Description |
| --- | --- | --- |
| `use_management` | `true` | If `false`, OpenVPN is started **without** `--management`. The tray uses **process running** (and optional `internal_ping_host`) for green/yellow; hover text shows **last action** (connect / disconnect / …). |
| `management_host` | `127.0.0.1` | Passed to `--management` when `use_management` is `true` |
| `management_port` | `7505` | TCP port when `use_management` is `true` (must be free) |
| `strip_profile_management` | `true` | Remove embedded `management …` lines from the profile so this app’s `--management` is used (fixes many Pritunl exports). |
| `management_hold_release` | `true` | Send `hold release` on the management socket when needed. |
| `internal_ping_host` | `null` | If set, when state is CONNECTED, ping this host before showing green (optional). |

## Other

| Field | Default | Description |
| --- | --- | --- |
| `log_directory` | `null` | If set, OpenVPN appends to `<dir>/openvpn.log`. |
| `tray_tooltip` | (see example) | Tray hover text. |
| `auto_connect` | `false` | Start OpenVPN once when the tray starts. |
| `notify_on_action` | `false` | Balloon when Connect/Disconnect/Reconnect is chosen. |
