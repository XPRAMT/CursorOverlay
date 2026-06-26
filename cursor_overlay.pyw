import ctypes
import sys
import winreg
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, QPoint, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap, QPolygon
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
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
STARTUP_APP_NAME = "CursorOverlay"
RUN_REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


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


def quote_windows_argument(value):
    return '"' + str(value).replace('"', r'\"') + '"'


class StartupManager:
    def __init__(self):
        self.python_path = Path(sys.executable)
        self.script_path = Path(__file__).resolve()

    def command(self):
        pythonw_path = self.python_path.with_name("pythonw.exe")
        executable = pythonw_path if pythonw_path.exists() else self.python_path
        return f"{quote_windows_argument(executable)} {quote_windows_argument(self.script_path)}"

    def is_enabled(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REGISTRY_PATH, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, STARTUP_APP_NAME)
        except FileNotFoundError:
            return False
        return value == self.command()

    def set_enabled(self, enabled):
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            RUN_REGISTRY_PATH,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(key, STARTUP_APP_NAME, 0, winreg.REG_SZ, self.command())
            else:
                try:
                    winreg.DeleteValue(key, STARTUP_APP_NAME)
                except FileNotFoundError:
                    pass


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
        self.draw_overlay = True

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
        self.apply_cursor_visibility()
        self.timer.start()

    def stop(self):
        self.timer.stop()
        self.visibility_guard.show()
        self.hide()
        self.destroy_current_icon()

    def set_hide_original(self, enabled):
        self.hide_original = enabled
        self.apply_cursor_visibility()

    def set_draw_overlay(self, enabled):
        self.draw_overlay = enabled
        if enabled:
            self.show()
        else:
            self.destroy_current_icon()
            self.hide()
        self.apply_cursor_visibility()
        self.update()

    def apply_cursor_visibility(self):
        if self.hide_original and self.draw_overlay and self.isVisible():
            self.visibility_guard.hide()
        else:
            self.visibility_guard.show()

    def refresh_cursor(self):
        if not self.draw_overlay:
            self.destroy_current_icon()
            self.update()
            return

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


def create_tray_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor("#0f172a"), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(QColor("#f8fafc"))
    pointer = QPolygon(
        [
            QPoint(14, 8),
            QPoint(14, 48),
            QPoint(27, 38),
            QPoint(35, 56),
            QPoint(44, 52),
            QPoint(36, 35),
            QPoint(52, 35),
        ]
    )
    painter.drawPolygon(pointer)
    painter.setPen(QPen(QColor("#38bdf8"), 5, Qt.SolidLine, Qt.RoundCap))
    painter.drawEllipse(38, 38, 16, 16)
    painter.end()
    return QIcon(pixmap)


class TrayController:
    def __init__(self, app, overlay, tray, startup_manager):
        self.app = app
        self.overlay = overlay
        self.tray = tray
        self.startup_manager = startup_manager

        self.menu = QMenu()
        self.status_action = QAction("Cursor overlay running")
        self.status_action.setEnabled(False)

        self.draw_action = QAction("Draw overlay cursor")
        self.draw_action.setCheckable(True)
        self.draw_action.setChecked(True)
        self.draw_action.toggled.connect(self.overlay.set_draw_overlay)

        self.hide_action = QAction("Hide original cursor")
        self.hide_action.setCheckable(True)
        self.hide_action.setChecked(True)
        self.hide_action.toggled.connect(self.overlay.set_hide_original)

        self.startup_action = QAction("Start with Windows")
        self.startup_action.setCheckable(True)
        self.startup_action.setChecked(self.startup_manager.is_enabled())
        self.startup_action.toggled.connect(self.set_startup_enabled)

        self.quit_action = QAction("Quit")
        self.quit_action.triggered.connect(self.quit)

        self.menu.aboutToShow.connect(self.overlay.visibility_guard.show)
        self.menu.aboutToHide.connect(self.restore_overlay_visibility)
        self.menu.addAction(self.status_action)
        self.menu.addSeparator()
        self.menu.addAction(self.draw_action)
        self.menu.addAction(self.hide_action)
        self.menu.addAction(self.startup_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.handle_activation)

    def handle_activation(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.menu.popup(self.tray.geometry().center())

    def restore_overlay_visibility(self):
        self.overlay.apply_cursor_visibility()

    def set_startup_enabled(self, enabled):
        self.startup_manager.set_enabled(enabled)
        blocker = QSignalBlocker(self.startup_action)
        self.startup_action.setChecked(self.startup_manager.is_enabled())
        del blocker

    def quit(self):
        self.overlay.stop()
        self.tray.hide()
        self.app.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    visibility_guard = CursorVisibilityGuard()
    overlay = OverlayWindow(CursorReader(), visibility_guard)

    tray = QSystemTrayIcon(create_tray_icon())
    tray.setToolTip("Cursor Overlay")
    tray_controller = TrayController(app, overlay, tray, StartupManager())
    tray.show()

    app.aboutToQuit.connect(overlay.stop)
    overlay.start()
    app.tray_controller = tray_controller
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
