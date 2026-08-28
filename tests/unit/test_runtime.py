from __future__ import annotations

import sys

from app.core.runtime import ensure_standard_streams


def test_ensure_standard_streams_replaces_missing_console_streams() -> None:
    originals = (sys.stdin, sys.stdout, sys.stderr)
    replacements = []
    try:
        sys.stdin = None
        sys.stdout = None
        sys.stderr = None

        replacements = ensure_standard_streams()

        assert len(replacements) == 3
        assert sys.stdin is not None
        assert sys.stdout is not None
        assert sys.stderr is not None
        assert isinstance(sys.stdout.isatty(), bool)
    finally:
        sys.stdin, sys.stdout, sys.stderr = originals
        for stream in replacements:
            stream.close()


def test_ensure_standard_streams_preserves_existing_streams() -> None:
    assert ensure_standard_streams() == []
