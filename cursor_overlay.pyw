import ctypes
import sys
import winreg
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, QPoint, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap, QPolygon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


user32 = ctypes.WinDLL("user32", use_last_error=True)

HWND_BROADCAST = wintypes.HWND(0xFFFF)
WM_SETTINGCHANGE = 0x001A
SMTO_ABORTIFHUNG = 0x0002
STARTUP_APP_NAME = "CursorOverlay"
RUN_REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REGISTRY_PATH = r"Software\CursorOverlay"
MOUSE_REGISTRY_PATH = r"Control Panel\Mouse"
MOUSE_TRAILS_VALUE = "MouseTrails"
ORIGINAL_MOUSE_TRAILS_VALUE = "OriginalMouseTrails"


user32.SendMessageTimeoutW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.POINTER(wintypes.DWORD),
]
user32.SendMessageTimeoutW.restype = wintypes.LPARAM


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


class PointerRenderingManager:
    def get_mouse_trails(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, MOUSE_REGISTRY_PATH, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, MOUSE_TRAILS_VALUE)
        except FileNotFoundError:
            return "0"
        return str(value)

    def set_mouse_trails(self, value):
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            MOUSE_REGISTRY_PATH,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, MOUSE_TRAILS_VALUE, 0, winreg.REG_SZ, str(value))
        self.broadcast_mouse_settings_changed()

    def is_forced(self):
        return self.get_mouse_trails() == "-1"

    def set_forced(self, enabled):
        if enabled:
            self.backup_original_value()
            self.set_mouse_trails("-1")
        else:
            self.set_mouse_trails(self.restore_original_value())

    def backup_original_value(self):
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            APP_REGISTRY_PATH,
            0,
            winreg.KEY_ALL_ACCESS,
        ) as key:
            try:
                winreg.QueryValueEx(key, ORIGINAL_MOUSE_TRAILS_VALUE)
            except FileNotFoundError:
                winreg.SetValueEx(
                    key,
                    ORIGINAL_MOUSE_TRAILS_VALUE,
                    0,
                    winreg.REG_SZ,
                    self.get_mouse_trails(),
                )

    def restore_original_value(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_REGISTRY_PATH, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, ORIGINAL_MOUSE_TRAILS_VALUE)
        except FileNotFoundError:
            return "0"

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_REGISTRY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, ORIGINAL_MOUSE_TRAILS_VALUE)
            except FileNotFoundError:
                pass
        return str(value)

    def broadcast_mouse_settings_changed(self):
        result = wintypes.DWORD()
        user32.SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            0,
            SMTO_ABORTIFHUNG,
            100,
            ctypes.byref(result),
        )


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
    def __init__(self, app, tray, startup_manager, pointer_rendering_manager):
        self.app = app
        self.tray = tray
        self.startup_manager = startup_manager
        self.pointer_rendering_manager = pointer_rendering_manager

        self.menu = QMenu()
        self.status_action = QAction("Software cursor path control")
        self.status_action.setEnabled(False)

        self.force_software_action = QAction("Force software cursor path")
        self.force_software_action.setCheckable(True)
        self.force_software_action.setChecked(self.pointer_rendering_manager.is_forced())
        self.force_software_action.toggled.connect(self.set_force_software_cursor_path)

        self.startup_action = QAction("Start with Windows")
        self.startup_action.setCheckable(True)
        self.startup_action.setChecked(self.startup_manager.is_enabled())
        self.startup_action.toggled.connect(self.set_startup_enabled)

        self.quit_action = QAction("Quit")
        self.quit_action.triggered.connect(self.quit)

        self.menu.addAction(self.status_action)
        self.menu.addSeparator()
        self.menu.addAction(self.force_software_action)
        self.menu.addAction(self.startup_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.handle_activation)

    def handle_activation(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.menu.popup(self.tray.geometry().center())

    def set_startup_enabled(self, enabled):
        self.startup_manager.set_enabled(enabled)
        blocker = QSignalBlocker(self.startup_action)
        self.startup_action.setChecked(self.startup_manager.is_enabled())
        del blocker

    def set_force_software_cursor_path(self, enabled):
        self.pointer_rendering_manager.set_forced(enabled)
        blocker = QSignalBlocker(self.force_software_action)
        self.force_software_action.setChecked(self.pointer_rendering_manager.is_forced())
        del blocker

    def quit(self):
        self.tray.hide()
        self.app.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    tray = QSystemTrayIcon(create_tray_icon())
    tray.setToolTip("Cursor Overlay")
    tray_controller = TrayController(app, tray, StartupManager(), PointerRenderingManager())
    tray.show()

    app.tray_controller = tray_controller
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
