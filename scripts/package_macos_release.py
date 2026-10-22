"""Audit a fresh application bundle, then create a release archive and checksum."""

from __future__ import annotations

import hashlib
import plistlib
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import __version__


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    bundle = root / "dist" / "MijiaDesktop.app"
    info = plistlib.loads((bundle / "Contents" / "Info.plist").read_bytes())
    if info["CFBundleShortVersionString"] != __version__:
        raise RuntimeError("Bundle version does not match source version")
    blocked_names = {
        "auth.json", "auth.dat", "auth.key", "mijia-login-qr.png", "qr.png",
        "direct_url.json", ".DS_Store", ".env", "settings.ini",
    }
    count = 0
    for path in bundle.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        if path.name in blocked_names or path.suffix.lower() in {
            ".log", ".db", ".sqlite", ".sqlite3",
        }:
            raise RuntimeError(f"Non-release application data found: {path.relative_to(bundle)}")
        data = path.read_bytes()
        # Always reject the actual local developer's home/project paths. Generic
        # hosted-runner paths carry no user's account information.
        if Path.home().name not in {"runner", "runneradmin"}:
            if (str(Path.home()).encode() + b"/") in data or str(root).encode() in data:
                raise RuntimeError(f"Local developer path found: {path.relative_to(bundle)}")
        homes = set(re.findall(rb"/Users/([^/\x00\s]{1,80})/", data))
        allowed = {b"runner", b"runneradmin", b"Shared", b"builder", b"buildbot", b"qt"}
        # Official CPython extension binaries may retain their vendor's build
        # directory in debug metadata. It is not the app developer's home path;
        # keep the exception limited to those upstream Mach-O extension files.
        vendor_python_binary = (
            (("lib-dynload" in path.parts and path.suffix == ".so")
             or "Python.framework" in path.parts
             or re.fullmatch(r"libpython\d+\.\d+\.dylib", path.name))
            and data[:4] in {b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe"}
        )
        if homes - allowed and not vendor_python_binary:
            raise RuntimeError(f"Developer home path found: {path.relative_to(bundle)}")
        count += 1
    archive = root / "dist" / f"MijiaDesktop-{__version__}-macos-arm64.zip"
    subprocess.run([
        "ditto", "-c", "-k", "--norsrc", "--keepParent", str(bundle), str(archive)
    ], check=True)
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    archive.with_suffix(".zip.sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="ascii"
    )
    print(f"Privacy audit passed for {count} bundle files")
    print(f"Release archive: {archive.name}")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
