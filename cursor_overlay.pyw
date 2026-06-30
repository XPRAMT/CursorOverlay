import sys
import winreg
import ctypes
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import QPoint, QSignalBlocker, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap, QPolygon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


STARTUP_APP_NAME = "CursorOverlay"
RUN_REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
kernel32.GetCurrentProcessId.argtypes = []
kernel32.GetCurrentProcessId.restype = wintypes.DWORD
kernel32.ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
kernel32.ProcessIdToSessionId.restype = wintypes.BOOL
shell32.ShellExecuteW.argtypes = [
    wintypes.HWND,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    ctypes.c_int,
]
shell32.ShellExecuteW.restype = wintypes.HINSTANCE


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


class DwmManager:
    def current_session_id(self):
        session_id = wintypes.DWORD()
        process_id = kernel32.GetCurrentProcessId()
        if not kernel32.ProcessIdToSessionId(process_id, ctypes.byref(session_id)):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(session_id.value)

    def restart(self):
        session_id = self.current_session_id()
        parameters = f'/f /fi "imagename eq dwm.exe" /fi "session eq {session_id}"'
        result = shell32.ShellExecuteW(
            None,
            "runas",
            "taskkill.exe",
            parameters,
            None,
            1,
        )
        if int(result) <= 32:
            if int(result) == 1223:
                raise OSError(1223, "Administrator approval was canceled")
            raise OSError(int(result), "ShellExecuteW runas failed")


def create_tray_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor("#111827"), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(QColor("#f9fafb"))
    pointer = QPolygon(
        [
            QPoint(15, 8),
            QPoint(15, 47),
            QPoint(27, 37),
            QPoint(35, 55),
            QPoint(44, 51),
            QPoint(36, 34),
            QPoint(51, 34),
        ]
    )
    painter.drawPolygon(pointer)
    painter.setPen(QPen(QColor("#10b981"), 5, Qt.SolidLine, Qt.RoundCap))
    painter.drawArc(38, 38, 16, 16, 20 * 16, 300 * 16)
    painter.end()
    return QIcon(pixmap)


class TrayController:
    def __init__(self, app, tray, startup_manager, dwm_manager):
        self.app = app
        self.tray = tray
        self.startup_manager = startup_manager
        self.dwm_manager = dwm_manager

        self.menu = QMenu()
        self.status_action = QAction("DWM restart workaround")
        self.status_action.setEnabled(False)

        self.restart_dwm_action = QAction("Restart Desktop Window Manager")
        self.restart_dwm_action.triggered.connect(self.restart_dwm)

        self.startup_action = QAction("Start with Windows")
        self.startup_action.setCheckable(True)
        self.startup_action.setChecked(self.startup_manager.is_enabled())
        self.startup_action.toggled.connect(self.set_startup_enabled)

        self.quit_action = QAction("Quit")
        self.quit_action.triggered.connect(self.quit)

        self.menu.addAction(self.status_action)
        self.menu.addSeparator()
        self.menu.addAction(self.restart_dwm_action)
        self.menu.addSeparator()
        self.menu.addAction(self.startup_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.handle_activation)

    def handle_activation(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.menu.popup(self.tray.geometry().center())

    def restart_dwm(self):
        self.restart_dwm_action.setEnabled(False)
        self.status_action.setText("Requesting administrator approval...")
        try:
            self.dwm_manager.restart()
        except OSError as error:
            self.status_action.setText("DWM restart failed")
            self.tray.showMessage("Cursor Overlay", f"Failed to restart DWM: {error}", QSystemTrayIcon.Warning)
        else:
            self.status_action.setText("DWM restart requested")
            self.tray.showMessage(
                "Cursor Overlay",
                "Administrator taskkill request was started.",
                QSystemTrayIcon.Information,
            )
        finally:
            self.restart_dwm_action.setEnabled(True)

    def set_startup_enabled(self, enabled):
        self.startup_manager.set_enabled(enabled)
        blocker = QSignalBlocker(self.startup_action)
        self.startup_action.setChecked(self.startup_manager.is_enabled())
        del blocker

    def quit(self):
        self.tray.hide()
        self.app.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    tray = QSystemTrayIcon(create_tray_icon())
    tray.setToolTip("Cursor Overlay")
    tray_controller = TrayController(app, tray, StartupManager(), DwmManager())
    tray.show()

    app.tray_controller = tray_controller
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
