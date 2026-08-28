"""Persistence repositories for user preferences."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core.exceptions import StorageError
from app.storage.database import open_database


class FavoritesRepository:
    def __init__(self, path: Path | None = None) -> None:
        try:
            self._connection = open_database(path)
        except sqlite3.Error as error:
            raise StorageError("无法打开本地收藏数据库") from error

    def list_dids(self) -> set[str]:
        try:
            rows = self._connection.execute("SELECT did FROM favorites").fetchall()
        except sqlite3.Error as error:
            raise StorageError("无法读取收藏设备") from error
        return {str(row[0]) for row in rows}

    def set_favorite(self, did: str, favorite: bool) -> None:
        try:
            if favorite:
                self._connection.execute(
                    "INSERT OR IGNORE INTO favorites (did) VALUES (?)",
                    (did,),
                )
            else:
                self._connection.execute("DELETE FROM favorites WHERE did = ?", (did,))
            self._connection.commit()
        except sqlite3.Error as error:
            raise StorageError("无法保存收藏设备") from error

    def close(self) -> None:
        self._connection.close()
