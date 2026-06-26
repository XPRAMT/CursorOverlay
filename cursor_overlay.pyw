import ctypes
import sys
import winreg
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, QPoint, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap, QPolygon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


user32 = ctypes.WinDLL("user32", use_last_error=True)

SPI_PRIVATE_SET_CURSOR_BASE_SIZE = 0x2029
SPIF_UPDATEINIFILE = 0x0001
SPIF_SENDCHANGE = 0x0002
STARTUP_APP_NAME = "CursorOverlay"
RUN_REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
ACCESSIBILITY_REGISTRY_PATH = r"Software\Microsoft\Accessibility"
CURSORS_REGISTRY_PATH = r"Control Panel\Cursors"
MOUSE_REGISTRY_PATH = r"Control Panel\Mouse"
CURSOR_SIZE_VALUE = "CursorSize"
CURSOR_BASE_SIZE_VALUE = "CursorBaseSize"
MOUSE_TRAILS_VALUE = "MouseTrails"


user32.SystemParametersInfoW.argtypes = [
    wintypes.UINT,
    wintypes.UINT,
    wintypes.LPVOID,
    wintypes.UINT,
]
user32.SystemParametersInfoW.restype = wintypes.BOOL


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
    def status_text(self):
        return (
            f"CursorSize={self.cursor_size()}  "
            f"CursorBaseSize={self.cursor_base_size()}  "
            f"MouseTrails={self.get_mouse_trails()}"
        )

    def get_dword(self, path, name, default=0):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, name)
        except FileNotFoundError:
            return default
        return int(value)

    def set_dword(self, path, name, value):
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, int(value))

    def cursor_size(self):
        return self.get_dword(ACCESSIBILITY_REGISTRY_PATH, CURSOR_SIZE_VALUE, 1)

    def cursor_base_size(self):
        return self.get_dword(CURSORS_REGISTRY_PATH, CURSOR_BASE_SIZE_VALUE, 32)

    def get_mouse_trails(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, MOUSE_REGISTRY_PATH, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, MOUSE_TRAILS_VALUE)
        except FileNotFoundError:
            return "0"
        return str(value)

    def apply_cursor_path_candidate(self, cursor_size, cursor_base_size):
        self.set_dword(ACCESSIBILITY_REGISTRY_PATH, CURSOR_SIZE_VALUE, cursor_size)
        ctypes.set_last_error(0)
        if not user32.SystemParametersInfoW(
            SPI_PRIVATE_SET_CURSOR_BASE_SIZE,
            0,
            ctypes.c_void_p(int(cursor_base_size)),
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
        ):
            error = ctypes.get_last_error()
            raise OSError(error, f"SystemParametersInfoW(0x2029, {cursor_base_size}) failed")


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
        self.status_action = QAction(self.pointer_rendering_manager.status_text())
        self.status_action.setEnabled(False)

        self.baseline_size1_action = QAction("Apply size 1 baseline (1 / 32)")
        self.baseline_size1_action.triggered.connect(lambda: self.apply_cursor_candidate(1, 32))

        self.gate_size7_action = QAction("Gate test (7 / 144)")
        self.gate_size7_action.triggered.connect(lambda: self.apply_cursor_candidate(7, 144))

        self.stable_size8_action = QAction("Apply size 8 stable (8 / 144)")
        self.stable_size8_action.triggered.connect(lambda: self.apply_cursor_candidate(8, 144))

        self.threshold_actions = []
        for cursor_base_size in (32, 48, 64, 80, 96, 112, 128):
            action = QAction(f"Threshold test (8 / {cursor_base_size})")
            action.triggered.connect(
                lambda checked=False, base_size=cursor_base_size: self.apply_cursor_candidate(8, base_size)
            )
            self.threshold_actions.append(action)

        self.startup_action = QAction("Start with Windows")
        self.startup_action.setCheckable(True)
        self.startup_action.setChecked(self.startup_manager.is_enabled())
        self.startup_action.toggled.connect(self.set_startup_enabled)

        self.quit_action = QAction("Quit")
        self.quit_action.triggered.connect(self.quit)

        self.menu.addAction(self.status_action)
        self.menu.addSeparator()
        self.menu.addAction(self.baseline_size1_action)
        self.menu.addAction(self.gate_size7_action)
        self.menu.addAction(self.stable_size8_action)
        for action in self.threshold_actions:
            self.menu.addAction(action)
        self.menu.addSeparator()
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

    def apply_cursor_candidate(self, cursor_size, cursor_base_size):
        self.pointer_rendering_manager.apply_cursor_path_candidate(cursor_size, cursor_base_size)
        self.refresh_status()

    def refresh_status(self):
        self.status_action.setText(self.pointer_rendering_manager.status_text())

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
