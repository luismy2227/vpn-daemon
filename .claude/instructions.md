We'll build a python vpn daemon that keeps me inside my vpn, even if wifi change, untill the vpn says its offline, or until we manually say it shouldn't be connected.

Context:
- we have the totp key
- currently we connect through pritunl (I think it uses open vpn under the hood, and I know for sure other teammembers use directly that)
- on `C:\Users\Luis2\AppData\Roaming\pritunl\profiles` we have .conf and .ovpn files for my profile. We can move them to a more centralized and easy to change place.
- Network Change Detection
- Reconnect if WiFi changes.
- Tray Icon

Tiny GUI with:
Connected 🟢
Reconnect
Disconnect

- use uv
- set a docs/ folder and document everything
- set a scripts/ folder and write ps1 files for installing/setting the project up, and for runing and exporting
- document important decisions on the docs folder
- test accordingly