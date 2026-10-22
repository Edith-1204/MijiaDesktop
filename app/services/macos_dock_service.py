"""Switch macOS between a foreground Dock app and a menu-bar-only accessory."""

from __future__ import annotations

import ctypes
import sys
from functools import lru_cache

from PySide6.QtGui import QGuiApplication


@lru_cache(maxsize=1)
def _native_application():
    ctypes.CDLL("/System/Library/Frameworks/AppKit.framework/AppKit")
    objc = ctypes.CDLL("/usr/lib/libobjc.A.dylib")
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    send = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(
        ("objc_msgSend", objc)
    )
    application = send(
        objc.objc_getClass(b"NSApplication"), objc.sel_registerName(b"sharedApplication")
    )
    set_policy = ctypes.CFUNCTYPE(
        ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long
    )(("objc_msgSend", objc))
    get_policy = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p)(
        ("objc_msgSend", objc)
    )
    return objc, application, set_policy, get_policy


def set_dock_visible(visible: bool) -> None:
    if sys.platform != "darwin" or QGuiApplication.platformName() != "cocoa":
        return
    objc, application, set_policy, get_policy = _native_application()
    target = 0 if visible else 1
    selector = objc.sel_registerName(b"activationPolicy")
    if get_policy(application, selector) == target:
        return
    set_policy(application, objc.sel_registerName(b"setActivationPolicy:"), target)
    if get_policy(application, selector) != target:
        raise RuntimeError("无法切换 macOS 程序坞显示状态")


def dock_is_visible() -> bool:
    objc, application, _set_policy, get_policy = _native_application()
    return get_policy(application, objc.sel_registerName(b"activationPolicy")) == 0
