# -*- mode: python ; coding: utf-8 -*-
r"""PyInstaller spec for vpn-daemon.exe

Build with:
    uv run pyinstaller vpn_daemon.spec --clean
or:
    .\scripts\build.ps1
"""

block_cipher = None

a = Analysis(
    ["src/vpn_daemon/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        ("img/vpn.ico", "img"),   # bundled so _load_base_icon() finds it via sys._MEIPASS
    ],
    hiddenimports=[
        "pystray._win32",
        "PIL._imaging",
        "PIL.Image",
        "PIL.ImageDraw",
        "keyring.backends",
        "keyring.backends.Windows",
        "keyring.core",
        "pyotp",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="vpn-daemon",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,        # no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,       # manifest requests elevation (no ShellExecute re-launch needed)
    icon="img/vpn.ico",   # .exe taskbar / file icon
)
