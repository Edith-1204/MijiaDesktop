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
        # Only generic runner/build-system home paths are allowed in packaged
        # dependencies. Developer home directories must never be distributed.
        data = path.read_bytes()
        homes = set(re.findall(rb"/Users/([^/\x00\s]{1,80})/", data))
        allowed = {b"runner", b"runneradmin", b"Shared", b"builder", b"buildbot", b"qt"}
        if homes - allowed:
            raise RuntimeError(f"Developer home path found: {path.relative_to(bundle)}")
        count += 1
    archive = root / "dist" / f"MijiaDesktop-{__version__}-macos-arm64.zip"
    subprocess.run([
        "ditto", "-c", "-k", "--norsrc", "--keepParent", str(bundle), str(archive)
    ], check=True)
    digest = hashlib.file_digest(archive.open("rb"), "sha256").hexdigest()
    archive.with_suffix(".zip.sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="ascii"
    )
    print(f"Privacy audit passed for {count} bundle files")
    print(f"Release archive: {archive.name}")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
