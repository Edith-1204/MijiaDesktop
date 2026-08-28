"""Phase 1 command-line proof of concept for real Mijia devices."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.core.exceptions import MijiaDesktopError
from app.mijia.adapter import MijiaAdapter


def json_value(raw_value: str) -> Any:
    """Parse booleans, numbers, lists, and quoted strings as JSON."""
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value


def require_confirmation(arguments: argparse.Namespace, operation: str) -> None:
    if not arguments.yes:
        raise ValueError(f"{operation} 会控制真实设备；确认参数无误后追加 --yes")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mijia Desktop Phase 1 PoC")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("login", help="扫码登录米家账号")
    commands.add_parser("status", help="验证登录状态")
    commands.add_parser("list", help="列出设备名称、Model 和 DID")

    spec = commands.add_parser("spec", help="读取型号的 MIoT Property 与 Action")
    spec.add_argument("--model", required=True)

    get_property = commands.add_parser("get", help="读取 Property")
    _add_property_identity(get_property)

    set_property = commands.add_parser("set", help="设置 Property")
    _add_property_identity(set_property)
    set_property.add_argument("--value", required=True, type=json_value)
    set_property.add_argument("--yes", action="store_true")

    action = commands.add_parser("action", help="执行 Action")
    action.add_argument("--did", required=True)
    action.add_argument("--siid", required=True, type=int)
    action.add_argument("--aiid", required=True, type=int)
    action.add_argument("--parameters", type=json_value, default=None)
    action.add_argument("--yes", action="store_true")

    commands.add_parser("logout", help="删除本机保存的登录状态")
    return parser


def _add_property_identity(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--did", required=True)
    parser.add_argument("--siid", required=True, type=int)
    parser.add_argument("--piid", required=True, type=int)


def run(arguments: argparse.Namespace, adapter: MijiaAdapter) -> int:
    if arguments.command == "login":
        adapter.login(lambda path: print(f"QR_CODE_PATH={path.resolve()}", flush=True))
        print("登录成功，认证数据已由 Windows DPAPI 加密保存。")
    elif arguments.command == "status":
        print("已登录" if adapter.is_authenticated() else "未登录或登录已失效")
    elif arguments.command == "list":
        devices = sorted(adapter.get_devices(), key=lambda item: item.get("name", ""))
        for device in devices:
            print(
                f"{device.get('name', '<unnamed>')}\t"
                f"Model={device.get('model', '<unknown>')}\t"
                f"DID={device.get('did', '<unknown>')}"
            )
        print(f"共 {len(devices)} 台设备")
    elif arguments.command == "spec":
        spec = adapter.get_device_spec(arguments.model)
        print(json.dumps(spec, ensure_ascii=False, indent=2))
    elif arguments.command == "get":
        result = adapter.get_properties(
            {"did": arguments.did, "siid": arguments.siid, "piid": arguments.piid}
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif arguments.command == "set":
        require_confirmation(arguments, "设置 Property")
        result = adapter.set_property(
            arguments.did, arguments.siid, arguments.piid, arguments.value
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif arguments.command == "action":
        require_confirmation(arguments, "执行 Action")
        parameters = arguments.parameters
        if parameters is not None and not isinstance(parameters, list):
            raise ValueError("--parameters 必须是 JSON 数组，例如 '[1, true]'")
        result = adapter.run_action(
            arguments.did, arguments.siid, arguments.aiid, parameters
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif arguments.command == "logout":
        adapter.clear_credentials()
        print("本机登录状态已删除。")
    return 0


def main() -> int:
    arguments = build_parser().parse_args()
    try:
        # Keep the short-lived QR image in an ignored, viewer-readable directory.
        qr_directory = Path.cwd() / "data" / "runtime"
        with MijiaAdapter(qr_directory=qr_directory) as adapter:
            return run(arguments, adapter)
    except (MijiaDesktopError, ValueError) as error:
        print(f"操作失败：{error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
