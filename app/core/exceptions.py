"""Application exceptions exposed above the third-party API boundary."""


class MijiaDesktopError(Exception):
    """Base class for errors safe to present through application services."""


class AuthenticationError(MijiaDesktopError):
    """Authentication is absent, expired, or rejected."""


class NetworkError(MijiaDesktopError):
    """The Xiaomi cloud could not be reached."""


class DeviceNotFoundError(MijiaDesktopError):
    """The requested device does not exist in the current account."""


class DeviceOfflineError(MijiaDesktopError):
    """The requested device is currently offline."""


class PropertyReadError(MijiaDesktopError):
    """A device property could not be read."""


class PropertyWriteError(MijiaDesktopError):
    """A device property could not be written."""


class ActionError(MijiaDesktopError):
    """A device action could not be executed."""


class UnsupportedDeviceError(MijiaDesktopError):
    """The requested capability is not supported by the device."""


class StorageError(MijiaDesktopError):
    """Local settings or favorites could not be persisted."""
