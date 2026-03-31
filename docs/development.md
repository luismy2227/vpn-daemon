# Development Guide

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

## Setup

```powershell
# Install all dependencies including dev tools
uv sync --group dev

# Install build tools (PyInstaller) when needed
uv sync --group build
```

## Running the app

```powershell
uv run python -m vpn_daemon
```

The app will prompt for UAC elevation on first run if not already elevated.
If credentials are missing from Windows Credential Manager, the setup wizard opens automatically.

## Running tests

Install the **dev** dependency group first (pytest lives there; `uv sync` alone is not enough):

```powershell
uv sync --group dev
```

Lint with **flake8** (configuration in `.flake8`):

```powershell
uv run flake8 src tests
```

Run all tests from the repository root:

```powershell
uv run pytest
```

Tests are fully isolated — no real OpenVPN process or network required.
The management socket tests use a local TCP mock server.

```powershell
# Verbose output
uv run pytest -v

# One file
uv run pytest tests/test_openvpn.py -v

# One test (node id)
uv run pytest tests/test_config.py::test_default_config_path_pyinstaller -v
```

On **GitHub**, push/PR to `main` or `master` runs the same checks (`.github/workflows/ci.yml`): `flake8` then `pytest` on Ubuntu with Python 3.11.

## Building the .exe

```powershell
.\scripts\build.ps1
```

Output: `dist\vpn-daemon.exe` — a standalone single-file executable that requests UAC elevation via its manifest (no Python required on the target machine).

The exe looks for `config\config.json` relative to its own directory. PyInstaller does **not** create that folder: on first run, if `config.json` is missing, the **setup wizard** opens so you can save settings (it creates `config\` next to the exe).

**Rebuild fails with `PermissionError: ... dist\vpn-daemon.exe`:** Windows cannot overwrite the exe while it is running. Quit the tray app, close Explorer windows that are showing `dist\`, then run `.\scripts\build.ps1` again.

## Project structure

```
src/vpn_daemon/
  __main__.py       Entry point, tray worker loop
  config.py         Config loading; CredentialsMissingError
  credentials.py    Windows Credential Manager wrapper (keyring)
  openvpn.py        OpenVPN subprocess + management socket
  otp.py            TOTP + PIN password builder
  setup_wizard.py   Tkinter setup UI
  tray_app.py       pystray icon, menu, and notifications

tests/
  test_config.py    Config loading, path resolution, keyring fallback
  test_otp.py       TOTP generation
  test_openvpn.py   State parsing, management socket, effective_link_state

scripts/
  build.ps1         PyInstaller one-file build
  install.ps1       Dev environment setup
  run.ps1           Launch from source
```

## Credentials storage

Sensitive fields (username, password, totp_secret) are stored in Windows Credential Manager under the service name `vpn-daemon`. Non-sensitive settings live in `config/config.json`.

To inspect stored credentials:
```powershell
# View via PowerShell
Get-StoredCredential -Target vpn-daemon  # requires CredentialManager module
```

Or open **Control Panel → Credential Manager → Windows Credentials** and look for `vpn-daemon` entries.

## Adding the app to Windows Task Scheduler (auto-start at logon)

```powershell
.\scripts\register-logon-task.ps1
```
