import ctypes
import json
import time
from ctypes import wintypes


user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

CURSOR_SHOWING = 0x00000001
IMAGE_BITMAP = 0


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hCursor", wintypes.HANDLE),
        ("ptScreenPos", POINT),
    ]


class ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", wintypes.BOOL),
        ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD),
        ("hbmMask", wintypes.HANDLE),
        ("hbmColor", wintypes.HANDLE),
    ]


class BITMAP(ctypes.Structure):
    _fields_ = [
        ("bmType", wintypes.LONG),
        ("bmWidth", wintypes.LONG),
        ("bmHeight", wintypes.LONG),
        ("bmWidthBytes", wintypes.LONG),
        ("bmPlanes", wintypes.WORD),
        ("bmBitsPixel", wintypes.WORD),
        ("bmBits", wintypes.LPVOID),
    ]


user32.GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]
user32.GetCursorInfo.restype = wintypes.BOOL
user32.GetIconInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ICONINFO)]
user32.GetIconInfo.restype = wintypes.BOOL
gdi32.GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID]
gdi32.GetObjectW.restype = ctypes.c_int
gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
gdi32.DeleteObject.restype = wintypes.BOOL


def bitmap_size(handle):
    if not handle:
        return None
    bitmap = BITMAP()
    if not gdi32.GetObjectW(handle, ctypes.sizeof(bitmap), ctypes.byref(bitmap)):
        return None
    return {"width": bitmap.bmWidth, "height": bitmap.bmHeight, "bits": bitmap.bmBitsPixel}


def snapshot():
    cursor_info = CURSORINFO()
    cursor_info.cbSize = ctypes.sizeof(CURSORINFO)
    if not user32.GetCursorInfo(ctypes.byref(cursor_info)):
        raise ctypes.WinError(ctypes.get_last_error())

    result = {
        "showing": bool(cursor_info.flags & CURSOR_SHOWING),
        "hcursor": int(cursor_info.hCursor or 0),
        "x": cursor_info.ptScreenPos.x,
        "y": cursor_info.ptScreenPos.y,
    }

    if cursor_info.hCursor:
        icon_info = ICONINFO()
        if user32.GetIconInfo(cursor_info.hCursor, ctypes.byref(icon_info)):
            result.update(
                {
                    "hotspot_x": icon_info.xHotspot,
                    "hotspot_y": icon_info.yHotspot,
                    "color_bitmap": bitmap_size(icon_info.hbmColor),
                    "mask_bitmap": bitmap_size(icon_info.hbmMask),
                }
            )
            if icon_info.hbmColor:
                gdi32.DeleteObject(icon_info.hbmColor)
            if icon_info.hbmMask:
                gdi32.DeleteObject(icon_info.hbmMask)
    return result


def main():
    last = None
    while True:
        current = snapshot()
        if current != last:
            print(json.dumps(current, ensure_ascii=False), flush=True)
            last = current
        time.sleep(0.25)


if __name__ == "__main__":
    main()
