"""Phase 2 proof of conversion from mijiaAPI data to unified models."""

from __future__ import annotations

from app.core.device_manager import DeviceManager
from app.core.exceptions import MijiaDesktopError
from app.mijia.adapter import MijiaAdapter


def main() -> int:
    try:
        with MijiaAdapter() as adapter:
            devices = DeviceManager(adapter).sync_devices()
        for device in devices:
            print(
                f"{device.name}\tType={device.device_type.value}\t"
                f"Capabilities={len(device.properties)}\tActions={len(device.actions)}"
            )
        print(f"Converted {len(devices)} devices")
        return 0
    except MijiaDesktopError as error:
        print(f"转换失败：{error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

