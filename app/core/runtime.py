"""Runtime compatibility helpers for GUI-only Windows processes."""

from __future__ import annotations

import os
import sys
from typing import TextIO


def ensure_standard_streams() -> list[TextIO]:
    """Provide harmless streams when a windowed executable has no console.

    PyInstaller's ``--windowed`` bootloader intentionally sets the standard
    streams to ``None``. Some third-party dependencies inspect ``isatty`` at
    import time, so give them a valid sink instead.
    """
    opened: list[TextIO] = []
    for name in ("stdin", "stdout", "stderr"):
        if getattr(sys, name) is not None:
            continue
        mode = "r" if name == "stdin" else "w"
        stream = open(os.devnull, mode, encoding="utf-8")  # noqa: SIM115
        setattr(sys, name, stream)
        opened.append(stream)
    return opened
