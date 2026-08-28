"""Load the Phase 3 application stylesheet."""

from pathlib import Path


def load_stylesheet(theme: str = "light") -> str:
    project_root = Path(__file__).resolve().parents[2]
    path = project_root / "resources" / "styles" / "main.qss"
    try:
        stylesheet = path.read_text(encoding="utf-8")
        if theme == "dark":
            dark_path = project_root / "resources" / "styles" / "dark.qss"
            stylesheet += "\n" + dark_path.read_text(encoding="utf-8")
        return stylesheet
    except OSError:
        return ""
