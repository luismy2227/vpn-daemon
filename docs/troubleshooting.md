# Troubleshooting

## Stuck “connecting” / icon never green

- Keep **`strip_profile_management`: true** if your `.ovpn` defines its own `management` port.
- Try another **`management_port`** if 7505 is taken.
- Set **`log_directory`** and read `openvpn.log` for auth or TLS errors.

## TOTP / PIN

- Use [`src/helper/otp.py`](../src/helper/otp.py) to print the same second-line password the app sends.
- System clock must be correct.

## Ctrl+C in the terminal

Use **Quit** from the tray, or close the terminal tab.

## Config not found

Set `VPN_DAEMON_CONFIG` or place `config.json` under `config/` in the repo.
