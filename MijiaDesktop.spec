# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys
import ssl


project_root = Path(SPECPATH)
is_macos = sys.platform == "darwin"
python_dlls = Path(sys.base_prefix) / "DLLs"
openssl_binaries = [
    (str(python_dlls / name), ".")
    for name in ("libcrypto-3-x64.dll", "libssl-3-x64.dll")
]
# Some Python distributions ship SSL policy data next to ssl.py. Freezing the
# module alone omits this dependency and SSLContext construction then raises
# FileNotFoundError before any HTTPS connection can be established.
ssl_policy_file = Path(ssl.__file__).with_name("codex-rejected-cas.pem")
runtime_data = [(str(ssl_policy_file), ".")] if ssl_policy_file.is_file() else []

analysis = Analysis(
    [str(project_root / "app" / "main.py")],
    pathex=[str(project_root)],
    # Pin the OpenSSL pair shipped with this Python runtime. Dependency
    # discovery can otherwise select an older same-named DLL from PATH, which
    # makes _ssl fail only when the first HTTPS request is made.
    binaries=[] if is_macos else openssl_binaries,
    datas=[(str(project_root / "resources"), "resources"), *runtime_data],
    hiddenimports=([] if is_macos else
                   ["win32crypt", "pywintypes", "win32timezone"]),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["keyring"] if is_macos else [],
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

if is_macos:
    executable = EXE(
        pyz,
        analysis.scripts,
        [],
        exclude_binaries=True,
        name="MijiaDesktop",
        console=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
    )
    collection = COLLECT(
        executable, analysis.binaries, analysis.datas,
        strip=False, upx=False, name="MijiaDesktop",
    )
    bundle = BUNDLE(
        collection,
        name="MijiaDesktop.app",
        icon=str(project_root / "resources" / "icons" / "mijia.icns"),
        bundle_identifier="io.github.Edith-1204.MijiaDesktop",
        info_plist={
            "CFBundleDisplayName": "米家桌面控制中心",
            "CFBundleShortVersionString": "1.3.0",
            "CFBundleVersion": "1.3.0",
            "NSHighResolutionCapable": True,
            "LSUIElement": True,
            "LSMinimumSystemVersion": "14.0",
        },
    )
else:
    executable = EXE(
        pyz,
        analysis.scripts,
        analysis.binaries,
        analysis.datas,
        [],
        name="MijiaDesktop-1.3.0",
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
