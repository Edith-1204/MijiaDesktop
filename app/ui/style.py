"""Load the Phase 3 application stylesheet."""

from pathlib import Path


def load_stylesheet() -> str:
    project_root = Path(__file__).resolve().parents[2]
    path = project_root / "resources" / "styles" / "main.qss"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""

