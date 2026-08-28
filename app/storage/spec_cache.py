"""Persistent MIoT specification cache."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.utils.logger import get_logger
from app.utils.paths import local_data_directory


logger = get_logger(__name__)


class DeviceSpecCache:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or local_data_directory() / "specs"

    def get(self, model: str) -> dict[str, Any] | None:
        path = self._path(model)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("model") != model or not isinstance(payload.get("spec"), dict):
                return None
            return payload["spec"]
        except (OSError, ValueError, TypeError) as error:
            logger.warning("Ignored invalid cached device specification: %s", error)
            return None

    def put(self, model: str, spec: dict[str, Any]) -> None:
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self._path(model)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps({"model": model, "spec": spec}, ensure_ascii=False),
                encoding="utf-8",
            )
            temporary.replace(path)
        except (OSError, TypeError, ValueError) as error:
            logger.warning("Could not cache device specification for model=%s: %s", model, error)

    def _path(self, model: str) -> Path:
        digest = hashlib.sha256(model.encode("utf-8")).hexdigest()
        return self.directory / f"{digest}.json"
