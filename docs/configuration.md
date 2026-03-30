# Configuration

Configuration is JSON. See [`config/config.example.json`](../config/config.example.json) for a full template.

## Credentials and paths

| Field | Description |
| --- | --- |
| `username` | VPN username |
| `password` | Static password (TOTP digits are appended automatically) |
| `totp_secret` | Base32 TOTP secret |
| `openvpn_path` | Full path to `openvpn.exe` |
| `profile` | Path to `.ovpn` / `.conf`, relative to the directory containing `config.json` unless absolute |

## OpenVPN management

| Field | Default | Description |
| --- | --- | --- |
| `management_host` | `127.0.0.1` | Management bind address (passed to OpenVPN) |
| `management_port` | `7505` | TCP port; must be free |

The daemon uses the management interface to distinguish connected vs still negotiating. If management is unreachable, status falls back to “process running” and optional ping (see below).

## Schedule (IANA timezone)

| Field | Description |
| --- | --- |
| `timezone` | IANA name, e.g. `America/New_York` (used by Python) |
| `work_days` | Short names: `mon`, `tue`, … |
| `work_hours_start` / `work_hours_end` | `HH:MM` in the configured timezone |
| `reconnect_outside_hours` | If `true`, auto-reconnect even outside the window; default `false` |

Outside work hours (when `reconnect_outside_hours` is `false`), the daemon does not auto-start or auto-reconnect. It does not force-disconnect an existing tunnel when the window ends.

## Optional Windows timezone (PowerShell only)

| Field | Description |
| --- | --- |
| `timezone_windows` | Windows timezone ID for `scripts/check-work-hours.ps1`, e.g. `Eastern Standard Time`. Not used by Python. Leave `null` if you do not use that script. List IDs with `tzutil /l` in a command prompt. |

## Network polling

| Field | Default | Description |
| --- | --- | --- |
| `network_poll_interval_seconds` | `5` | How often to sample network signature |
| `network_reconnect_debounce_seconds` | `3` | Delay after a change before triggering reconnect |
| `network_ignore_seconds_after_vpn_start` | `60` | Ignore “network changed” restarts for this long after each successful OpenVPN start (stops VPN‑adapter churn from looping) |

Wi‑Fi: the signature is `wlan:<your SSID>` so adding a VPN virtual adapter does not change it. Ethernet: profiles are filtered to drop common VPN/TAP/Wintun interface names; extend the filter in `src/vpn_daemon/network.py` if your adapter is still misclassified.

## Health check

| Field | Description |
| --- | --- |
| `internal_ping_host` | If set, when management reports `CONNECTED`, the daemon pings this host (`ping -n 1`); failure treats the link as not ready for “connected” UI. Optional. |

## Logging

| Field | Description |
| --- | --- |
| `log_directory` | If set, OpenVPN gets `--log-append <dir>/openvpn.log` |

## Intervals

| Field | Default | Description |
| --- | --- | --- |
| `check_interval_seconds` | `30` | How often the core loop re-evaluates auto-reconnect policy |
