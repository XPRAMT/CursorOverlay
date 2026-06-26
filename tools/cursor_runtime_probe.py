import argparse
import ctypes
import json
import subprocess
import sys
import time
import winreg
from ctypes import wintypes


user32 = ctypes.WinDLL("user32", use_last_error=True)

SPIF_UPDATEINIFILE = 0x0001
SPIF_SENDCHANGE = 0x0002
SPI_SETCURSORS = 0x0057
SPI_GETMOUSETRAILS = 0x005E
SPI_PRIVATE_SET_CURSOR_BASE_SIZE = 0x2029
SM_CXCURSOR = 13
SM_CYCURSOR = 14
ACCESSIBILITY_REGISTRY_PATH = r"Software\Microsoft\Accessibility"
CURSORS_REGISTRY_PATH = r"Control Panel\Cursors"
MOUSE_REGISTRY_PATH = r"Control Panel\Mouse"


user32.SystemParametersInfoW.argtypes = [
    wintypes.UINT,
    wintypes.UINT,
    wintypes.LPVOID,
    wintypes.UINT,
]
user32.SystemParametersInfoW.restype = wintypes.BOOL
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.SendNotifyMessageW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.SendNotifyMessageW.restype = wintypes.BOOL


def read_value(path, name, default=None):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ) as key:
            value, value_type = winreg.QueryValueEx(key, name)
    except FileNotFoundError:
        return default
    return {"value": value, "type": value_type}


def write_dword(path, name, value):
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, int(value))


def mouse_trails():
    value = wintypes.UINT()
    if user32.SystemParametersInfoW(SPI_GETMOUSETRAILS, 0, ctypes.byref(value), 0):
        return value.value
    return None


def snapshot():
    return {
        "cursor_size": read_value(ACCESSIBILITY_REGISTRY_PATH, "CursorSize"),
        "cursor_base_size": read_value(CURSORS_REGISTRY_PATH, "CursorBaseSize"),
        "mouse_trails_registry": read_value(MOUSE_REGISTRY_PATH, "MouseTrails"),
        "mouse_trails_spi": mouse_trails(),
        "sm_cxcursor": user32.GetSystemMetrics(SM_CXCURSOR),
        "sm_cycursor": user32.GetSystemMetrics(SM_CYCURSOR),
    }


def spi(action, ui_param=0, pv_param=None, flags=SPIF_UPDATEINIFILE | SPIF_SENDCHANGE):
    ctypes.set_last_error(0)
    result = bool(user32.SystemParametersInfoW(action, ui_param, pv_param, flags))
    return {"result": result, "last_error_if_failed": None if result else ctypes.get_last_error()}


def apply_registry(cursor_size, cursor_base_size):
    if cursor_size is not None:
        write_dword(ACCESSIBILITY_REGISTRY_PATH, "CursorSize", cursor_size)
    if cursor_base_size is not None:
        write_dword(CURSORS_REGISTRY_PATH, "CursorBaseSize", cursor_base_size)


def broadcast_update_per_user_system_parameters():
    completed = subprocess.run(
        ["rundll32.exe", "user32.dll,UpdatePerUserSystemParameters"],
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def run_apply(args):
    before = snapshot()
    if not args.skip_registry:
        apply_registry(args.cursor_size, args.cursor_base_size)

    calls = []
    if args.method == "spi_setcursors":
        calls.append({"method": args.method, **spi(SPI_SETCURSORS)})
    elif args.method == "spi_2029_ui_param":
        calls.append(
            {
                "method": args.method,
                **spi(SPI_PRIVATE_SET_CURSOR_BASE_SIZE, args.cursor_base_size or 0),
            }
        )
    elif args.method == "spi_2029_pv_value":
        calls.append(
            {
                "method": args.method,
                **spi(SPI_PRIVATE_SET_CURSOR_BASE_SIZE, 0, ctypes.c_void_p(args.cursor_base_size or 0)),
            }
        )
    elif args.method == "rundll32":
        calls.append({"method": args.method, **broadcast_update_per_user_system_parameters()})
    elif args.method == "registry_only":
        calls.append({"method": args.method, "result": "registry written only"})
    else:
        raise ValueError(f"unknown method: {args.method}")

    time.sleep(args.delay)
    after = snapshot()
    return {"before": before, "calls": calls, "after": after}


def run_sequence(args):
    results = []
    for method in [
        "registry_only",
        "rundll32",
        "spi_setcursors",
        "spi_2029_ui_param",
        "spi_2029_pv_value",
    ]:
        sequence_args = argparse.Namespace(
            cursor_size=args.cursor_size,
            cursor_base_size=args.cursor_base_size,
            method=method,
            delay=args.delay,
            skip_registry=False,
        )
        results.append(run_apply(sequence_args))
    return results


def main():
    parser = argparse.ArgumentParser(description="Probe Windows cursor runtime apply paths.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("snapshot")

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--cursor-size", type=int)
    apply_parser.add_argument("--cursor-base-size", type=int)
    apply_parser.add_argument(
        "--method",
        choices=[
            "registry_only",
            "rundll32",
            "spi_setcursors",
            "spi_2029_ui_param",
            "spi_2029_pv_value",
        ],
        required=True,
    )
    apply_parser.add_argument(
        "--skip-registry",
        action="store_true",
        help="Call the runtime method without writing CursorSize/CursorBaseSize first.",
    )
    apply_parser.add_argument("--delay", type=float, default=0.25)

    sequence_parser = subparsers.add_parser("sequence")
    sequence_parser.add_argument("--cursor-size", type=int, required=True)
    sequence_parser.add_argument("--cursor-base-size", type=int, required=True)
    sequence_parser.add_argument("--delay", type=float, default=0.25)

    args = parser.parse_args()
    if args.command == "snapshot":
        output = snapshot()
    elif args.command == "apply":
        output = run_apply(args)
    else:
        output = run_sequence(args)

    json.dump(output, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
