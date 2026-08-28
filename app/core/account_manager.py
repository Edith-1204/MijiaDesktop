"""Account lifecycle service."""

from app.mijia.adapter import MijiaAdapter


class AccountManager:
    """Coordinate authentication without exposing third-party API objects."""

    def __init__(self, adapter: MijiaAdapter) -> None:
        self._adapter = adapter

    def login(self) -> None:
        self._adapter.login()

    def logout(self) -> None:
        self._adapter.clear_credentials()

    def is_authenticated(self) -> bool:
        return self._adapter.is_authenticated()

    def ensure_authenticated(self) -> None:
        if not self.is_authenticated():
            self.login()

