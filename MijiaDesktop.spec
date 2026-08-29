# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys


project_root = Path(SPECPATH)
python_dlls = Path(sys.base_prefix) / "DLLs"
openssl_binaries = [
    (str(python_dlls / name), ".")
    for name in ("libcrypto-3-x64.dll", "libssl-3-x64.dll")
]

analysis = Analysis(
    [str(project_root / "app" / "main.py")],
    pathex=[str(project_root)],
    # Pin the OpenSSL pair shipped with this Python runtime. Dependency
    # discovery can otherwise select an older same-named DLL from PATH, which
    # makes _ssl fail only when the first HTTPS request is made.
    binaries=openssl_binaries,
    datas=[(str(project_root / "resources"), "resources")],
    hiddenimports=["win32crypt", "pywintypes", "win32timezone"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
# PySide6 uses Windows' ICU API. Unrelated toolchains may expose same-named ICU
# DLLs to the build process; bundling them shadows the system API and breaks Qt.
analysis.binaries = type(analysis.binaries)(
    entry for entry in analysis.binaries
    if Path(entry[0]).name.lower() not in {"icuuc.dll", "icudt78.dll", "icuin.dll"}
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="MijiaDesktop-1.0.0",
    icon=str(project_root / "resources" / "icons" / "mijia.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(project_root / "packaging" / "windows_version_info.txt"),
)
