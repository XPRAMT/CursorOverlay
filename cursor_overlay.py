import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QLabel,
    QMainWindow,
    QSystemTrayIcon,
    QWidget,
)


user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

CURSOR_SHOWING = 0x00000001
DI_NORMAL = 0x0003
HWND_TOPMOST = wintypes.HWND(-1)
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
OVERLAY_SIZE = 256
OVERLAY_PADDING = OVERLAY_SIZE // 2


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]


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
        ("hbmMask", wintypes.HBITMAP),
        ("hbmColor", wintypes.HBITMAP),
    ]


user32.GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]
user32.GetCursorInfo.restype = wintypes.BOOL
user32.GetIconInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ICONINFO)]
user32.GetIconInfo.restype = wintypes.BOOL
user32.CopyIcon.argtypes = [wintypes.HANDLE]
user32.CopyIcon.restype = wintypes.HANDLE
user32.DestroyIcon.argtypes = [wintypes.HANDLE]
user32.DestroyIcon.restype = wintypes.BOOL
user32.DrawIconEx.argtypes = [
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HANDLE,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
    wintypes.HBRUSH,
    wintypes.UINT,
]
user32.DrawIconEx.restype = wintypes.BOOL
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int
user32.ShowCursor.argtypes = [wintypes.BOOL]
user32.ShowCursor.restype = ctypes.c_int
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.SetWindowPos.restype = wintypes.BOOL
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL


def raise_last_winerror(action):
    error = ctypes.get_last_error()
    raise ctypes.WinError(error, action)


class CursorState:
    def __init__(self, x, y, cursor, hotspot_x, hotspot_y, is_visible):
        self.x = x
        self.y = y
        self.cursor = cursor
        self.hotspot_x = hotspot_x
        self.hotspot_y = hotspot_y
        self.is_visible = is_visible


class CursorReader:
    def read(self):
        info = CURSORINFO()
        info.cbSize = ctypes.sizeof(CURSORINFO)
        if not user32.GetCursorInfo(ctypes.byref(info)):
            raise_last_winerror("GetCursorInfo failed")
        if not info.hCursor:
            return None

        icon = user32.CopyIcon(info.hCursor)
        if not icon:
            raise_last_winerror("CopyIcon failed")

        icon_info = ICONINFO()
        if not user32.GetIconInfo(icon, ctypes.byref(icon_info)):
            user32.DestroyIcon(icon)
            raise_last_winerror("GetIconInfo failed")

        if icon_info.hbmMask:
            gdi32.DeleteObject(icon_info.hbmMask)
        if icon_info.hbmColor:
            gdi32.DeleteObject(icon_info.hbmColor)

        return CursorState(
            info.ptScreenPos.x,
            info.ptScreenPos.y,
            icon,
            int(icon_info.xHotspot),
            int(icon_info.yHotspot),
            bool(info.flags & CURSOR_SHOWING),
        )


class CursorVisibilityGuard:
    def __init__(self):
        self.enabled = False
        self.hide_calls = 0

    def hide(self):
        if self.enabled:
            return
        self.enabled = True
        self.hide_calls = 0
        while user32.ShowCursor(False) >= 0 and self.hide_calls < 64:
            self.hide_calls += 1

    def show(self):
        if not self.enabled:
            return
        while user32.ShowCursor(True) < 0:
            pass
        self.enabled = False
        self.hide_calls = 0


class OverlayWindow(QWidget):
    def __init__(self, reader, visibility_guard):
        super().__init__()
        self.reader = reader
        self.visibility_guard = visibility_guard
        self.cursor_state = None
        self.hide_original = True

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput
            | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(OVERLAY_SIZE, OVERLAY_SIZE)

        self.timer = QTimer(self)
        self.timer.setInterval(8)
        self.timer.timeout.connect(self.refresh_cursor)

    def start(self):
        self.show()
        if self.hide_original:
            self.visibility_guard.hide()
        self.timer.start()

    def stop(self):
        self.timer.stop()
        self.visibility_guard.show()
        self.hide()
        self.destroy_current_icon()

    def set_hide_original(self, enabled):
        self.hide_original = enabled
        if enabled and self.isVisible():
            self.visibility_guard.hide()
        else:
            self.visibility_guard.show()

    def refresh_cursor(self):
        state = self.reader.read()
        self.destroy_current_icon()
        self.cursor_state = state
        if state:
            self.move(state.x - OVERLAY_PADDING, state.y - OVERLAY_PADDING)
            self.keep_above_application_windows()
        self.update()

    def keep_above_application_windows(self):
        user32.SetWindowPos(
            int(self.winId()),
            HWND_TOPMOST,
            self.x(),
            self.y(),
            0,
            0,
            SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )

    def destroy_current_icon(self):
        if self.cursor_state and self.cursor_state.cursor:
            user32.DestroyIcon(self.cursor_state.cursor)
        self.cursor_state = None

    def paintEvent(self, event):
        if not self.cursor_state:
            return

        hdc = user32.GetDC(int(self.winId()))
        if not hdc:
            return

        try:
            draw_x = OVERLAY_PADDING - self.cursor_state.hotspot_x
            draw_y = OVERLAY_PADDING - self.cursor_state.hotspot_y
            user32.DrawIconEx(
                hdc,
                draw_x,
                draw_y,
                self.cursor_state.cursor,
                0,
                0,
                0,
                None,
                DI_NORMAL,
            )
        finally:
            user32.ReleaseDC(int(self.winId()), hdc)


class ControlWindow(QMainWindow):
    def __init__(self, overlay):
        super().__init__()
        self.overlay = overlay
        self.setWindowTitle("Cursor Overlay")
        self.setFixedWidth(320)
        self.setCursor(Qt.BlankCursor)

        self.status_label = QLabel("Overlay running")
        self.hide_checkbox = QCheckBox("Hide original cursor")
        self.hide_checkbox.setChecked(True)
        self.hide_checkbox.toggled.connect(self.overlay.set_hide_original)

        layout = QFormLayout()
        layout.addRow("Status", self.status_label)
        layout.addRow(self.hide_checkbox)

        central = QWidget()
        central.setCursor(Qt.BlankCursor)
        central.setLayout(layout)
        self.setCentralWidget(central)

    def closeEvent(self, event):
        self.overlay.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    visibility_guard = CursorVisibilityGuard()
    overlay = OverlayWindow(CursorReader(), visibility_guard)
    control = ControlWindow(overlay)

    tray = QSystemTrayIcon(app.style().standardIcon(QApplication.style().StandardPixmap.SP_ComputerIcon))
    show_action = QAction("Show controls")
    quit_action = QAction("Quit")
    show_action.triggered.connect(control.show)
    quit_action.triggered.connect(app.quit)
    tray_menu = tray.contextMenu() or None
    if tray_menu is None:
        from PySide6.QtWidgets import QMenu

        tray_menu = QMenu()
    tray_menu.addAction(show_action)
    tray_menu.addAction(quit_action)
    tray.setContextMenu(tray_menu)
    tray.show()

    app.aboutToQuit.connect(overlay.stop)
    overlay.start()
    control.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
