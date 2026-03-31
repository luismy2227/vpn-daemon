"""Tkinter setup wizard for VPN daemon configuration."""

from __future__ import annotations

import json
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
from pathlib import Path
from typing import Any

import pyotp

from vpn_daemon.config import default_config_path
from vpn_daemon.credentials import clear_credentials, load_credentials, save_credentials

# Return values from run_setup_wizard
SAVED    = "saved"
CANCELLED = "cancelled"
CLEARED  = "cleared"


def _load_existing_json(config_path: Path) -> dict[str, Any]:
    if config_path.is_file():
        try:
            with config_path.open(encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_json(config_path: Path, data: dict[str, Any]) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def run_setup_wizard(config_path: Path | None = None) -> str:
    """Open the setup wizard and block until it is closed.

    Returns one of the module-level constants: SAVED, CANCELLED, or CLEARED.
    Intended to be called from a dedicated thread (not the pystray main thread).
    """
    if config_path is None:
        config_path = default_config_path()

    result: list[str] = [CANCELLED]

    existing_json = _load_existing_json(config_path)
    existing_creds = load_credentials()

    root = tk.Tk()
    root.title("VPN Daemon — Setup")
    root.resizable(False, False)

    PAD = {"padx": 8, "pady": 4}

    def _section(parent: tk.Widget, text: str) -> tk.LabelFrame:
        lf = tk.LabelFrame(parent, text=text, font=("Segoe UI", 9, "bold"), padx=6, pady=6)
        lf.pack(fill="x", padx=10, pady=(8, 0))
        return lf

    def _row(parent: tk.Widget, label: str, var: tk.Variable, show: str = "") -> tk.Entry:
        row = tk.Frame(parent)
        row.pack(fill="x", **PAD)
        tk.Label(row, text=label, width=18, anchor="w", font=("Segoe UI", 9)).pack(side="left")
        entry = tk.Entry(row, textvariable=var, show=show, font=("Segoe UI", 9), width=36)
        entry.pack(side="left", fill="x", expand=True)
        return entry

    def _browse_file(var: tk.StringVar, filetypes: list[tuple[str, str]]) -> None:
        path = fd.askopenfilename(filetypes=filetypes)
        if path:
            var.set(path)

    def _browse_dir(var: tk.StringVar) -> None:
        path = fd.askdirectory()
        if path:
            var.set(path)

    # ── Credentials ──────────────────────────────────────────────────────────
    cred_frame = _section(root, "Credentials  (saved to Windows Credential Manager)")

    v_username = tk.StringVar(value=existing_creds[0] if existing_creds else existing_json.get("username", ""))
    v_password = tk.StringVar(value=existing_creds[1] if existing_creds else existing_json.get("password", ""))
    v_totp = tk.StringVar(value=existing_creds[2] if existing_creds else existing_json.get("totp_secret", ""))

    _row(cred_frame, "Username:", v_username)
    _row(cred_frame, "Password (PIN):", v_password, show="•")

    totp_row = tk.Frame(cred_frame)
    totp_row.pack(fill="x", **PAD)
    tk.Label(totp_row, text="TOTP Secret:", width=18, anchor="w", font=("Segoe UI", 9)).pack(side="left")
    tk.Entry(totp_row, textvariable=v_totp, font=("Segoe UI", 9), width=28).pack(side="left", fill="x", expand=True)

    def _test_totp() -> None:
        secret = v_totp.get().strip()
        if not secret:
            mb.showwarning("TOTP Test", "Enter a TOTP secret first.", parent=root)
            return
        try:
            code = pyotp.TOTP(secret).now()
            mb.showinfo("TOTP Test", f"Current code: {code}\n\nThis is what will be appended to your password.", parent=root)
        except Exception as e:
            mb.showerror("TOTP Test", f"Invalid secret: {e}", parent=root)

    tk.Button(totp_row, text="Test ▶", command=_test_totp, font=("Segoe UI", 9)).pack(side="left", padx=(4, 0))

    # ── Paths ─────────────────────────────────────────────────────────────────
    path_frame = _section(root, "Paths")

    default_ovpn = r"C:\Program Files\OpenVPN\bin\openvpn.exe"
    v_openvpn = tk.StringVar(value=existing_json.get("openvpn_path", default_ovpn))
    v_profile = tk.StringVar(value=existing_json.get("profile", ""))

    def _path_row(parent: tk.Widget, label: str, var: tk.StringVar, is_dir: bool = False,
                  filetypes: list[tuple[str, str]] | None = None) -> None:
        row = tk.Frame(parent)
        row.pack(fill="x", **PAD)
        tk.Label(row, text=label, width=18, anchor="w", font=("Segoe UI", 9)).pack(side="left")
        tk.Entry(row, textvariable=var, font=("Segoe UI", 9), width=32).pack(side="left", fill="x", expand=True)
        cmd = (lambda v=var: _browse_dir(v)) if is_dir else (lambda v=var, ft=filetypes or []: _browse_file(v, ft))
        tk.Button(row, text="Browse…", command=cmd, font=("Segoe UI", 9)).pack(side="left", padx=(4, 0))

    _path_row(path_frame, "OpenVPN exe:", v_openvpn,
              filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
    _path_row(path_frame, ".ovpn profile:", v_profile,
              filetypes=[("OpenVPN profile", "*.ovpn *.conf"), ("All files", "*.*")])

    # ── Options ───────────────────────────────────────────────────────────────
    opt_frame = _section(root, "Options")

    v_auto_connect = tk.BooleanVar(value=bool(existing_json.get("auto_connect", False)))
    v_notify = tk.BooleanVar(value=bool(existing_json.get("notify_on_action", False)))
    v_log_dir = tk.StringVar(value=existing_json.get("log_directory") or "")
    v_tooltip = tk.StringVar(value=existing_json.get("tray_tooltip", "VPN \u2014 right-click for menu"))

    tk.Checkbutton(opt_frame, text="Auto-connect on startup", variable=v_auto_connect,
                   font=("Segoe UI", 9)).pack(anchor="w", padx=8)
    tk.Checkbutton(opt_frame, text="Show notifications on state changes",
                   variable=v_notify, font=("Segoe UI", 9)).pack(anchor="w", padx=8)

    _path_row(opt_frame, "Log folder:", v_log_dir, is_dir=True)
    _row(opt_frame, "Tray label:", v_tooltip)

    # ── Buttons ───────────────────────────────────────────────────────────────
    btn_frame = tk.Frame(root)
    btn_frame.pack(fill="x", padx=10, pady=10)

    def _save() -> None:
        username = v_username.get().strip()
        password = v_password.get().strip()
        totp_secret = v_totp.get().strip()
        openvpn_path = v_openvpn.get().strip()
        profile = v_profile.get().strip()

        if not all([username, totp_secret, openvpn_path, profile]):
            mb.showerror("Validation", "Username, TOTP Secret, OpenVPN path, and Profile are required.", parent=root)
            return

        try:
            pyotp.TOTP(totp_secret).now()
        except Exception:
            mb.showerror("Validation", "TOTP Secret is not a valid Base32 string.", parent=root)
            return

        save_credentials(username, password, totp_secret)

        data = _load_existing_json(config_path)
        for k in ("username", "password", "totp_secret"):
            data.pop(k, None)

        data["openvpn_path"] = openvpn_path
        data["profile"] = profile
        data["auto_connect"] = v_auto_connect.get()
        data["notify_on_action"] = v_notify.get()
        data["tray_tooltip"] = v_tooltip.get()

        log_dir = v_log_dir.get().strip()
        data["log_directory"] = log_dir if log_dir else None

        _save_json(config_path, data)
        result[0] = SAVED
        root.destroy()

    def _clear_all() -> None:
        confirmed = mb.askyesno(
            "Clear All Settings",
            "This will permanently erase:\n"
            "  \u2022  All credentials from Windows Credential Manager\n"
            "  \u2022  Your configuration file (config.json)\n\n"
            "The application will exit so you can start fresh.\n\n"
            "Are you sure?",
            icon="warning",
            parent=root,
        )
        if not confirmed:
            return

        clear_credentials()
        try:
            config_path.unlink(missing_ok=True)
        except OSError:
            pass

        mb.showinfo(
            "Settings Cleared",
            "All settings and credentials have been erased.\n\n"
            "The application will now exit. Re-launch to configure from scratch.",
            parent=root,
        )
        result[0] = CLEARED
        root.destroy()

    def _cancel() -> None:
        root.destroy()

    # Clear All — far left, red to signal destructive action
    tk.Button(
        btn_frame, text="Clear All Settings", command=_clear_all,
        font=("Segoe UI", 9), fg="white", bg="#c42b1c",
    ).pack(side="left")

    tk.Button(btn_frame, text="Save", command=_save, font=("Segoe UI", 9),
              width=10, bg="#0078d4", fg="white").pack(side="right", padx=(4, 0))
    tk.Button(btn_frame, text="Cancel", command=_cancel,
              font=("Segoe UI", 9), width=10).pack(side="right")

    root.update_idletasks()
    w, h = root.winfo_reqwidth(), root.winfo_reqheight()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    root.mainloop()
    return result[0]
