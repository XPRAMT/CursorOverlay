import ctypes
import json
import sys
import winreg
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSignalBlocker, QPoint, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QImage, QImageReader, QPainter, QPen, QPixmap, QPolygon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


user32 = ctypes.WinDLL("user32", use_last_error=True)

SPI_PRIVATE_SET_CURSOR_BASE_SIZE = 0x2029
SPI_SETCURSORS = 0x0057
SPIF_UPDATEINIFILE = 0x0001
SPIF_SENDCHANGE = 0x0002
STABLE_CURSOR_BASE_SIZE = 144
DEFAULT_CURSOR_BASE_SIZE = 32
PADDED_CURSOR_CANVAS_SIZE = 144
DEFAULT_PADDED_CURSOR_GLYPH_SIZE = 48
STARTUP_APP_NAME = "CursorOverlay"
RUN_REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REGISTRY_PATH = r"Software\CursorOverlay"
ACCESSIBILITY_REGISTRY_PATH = r"Software\Microsoft\Accessibility"
CURSORS_REGISTRY_PATH = r"Control Panel\Cursors"
MOUSE_REGISTRY_PATH = r"Control Panel\Mouse"
CURSOR_SIZE_VALUE = "CursorSize"
CURSOR_BASE_SIZE_VALUE = "CursorBaseSize"
MOUSE_TRAILS_VALUE = "MouseTrails"
ORIGINAL_CURSORS_VALUE = "OriginalCursors"
PADDED_GLYPH_SIZE_VALUE = "PaddedGlyphSize"
PADDED_SCHEME_NAME = "CursorOverlay Padded Small"
FALLBACK_CURSOR_ROLES = {
    "Arrow": "aero_arrow.cur",
    "Help": "aero_helpsel.cur",
    "Hand": "aero_link.cur",
    "No": "aero_unavail.cur",
    "SizeNS": "aero_ns.cur",
    "SizeWE": "aero_ew.cur",
    "SizeNWSE": "aero_nwse.cur",
    "SizeNESW": "aero_nesw.cur",
    "SizeAll": "aero_move.cur",
    "NWPen": "aero_pen.cur",
    "UpArrow": "aero_up.cur",
    "Pin": "aero_pin.cur",
    "Person": "aero_person.cur",
    "IBeam": "beam_r.cur",
    "Crosshair": "cross_r.cur",
    "Wait": "wait_r.cur",
    "AppStarting": "busy_r.cur",
}
SCHEME_ROLE_ORDER = [
    "Arrow",
    "Help",
    "AppStarting",
    "Wait",
    "Crosshair",
    "IBeam",
    "NWPen",
    "No",
    "SizeNS",
    "SizeWE",
    "SizeNWSE",
    "SizeNESW",
    "SizeAll",
    "UpArrow",
    "Hand",
    "Pin",
    "Person",
]


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
            f"GlyphSize={self.padded_glyph_size()}  "
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

    def get_registry_string(self, path, name, default=""):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, name)
        except FileNotFoundError:
            return default
        return str(value)

    def set_registry_string(self, path, name, value):
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, str(value))

    def padded_glyph_size(self):
        value = self.get_dword(APP_REGISTRY_PATH, PADDED_GLYPH_SIZE_VALUE, DEFAULT_PADDED_CURSOR_GLYPH_SIZE)
        return max(16, min(PADDED_CURSOR_CANVAS_SIZE, value))

    def set_padded_glyph_size(self, value):
        self.set_dword(APP_REGISTRY_PATH, PADDED_GLYPH_SIZE_VALUE, value)

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

    def apply_cursor_base_size(self, cursor_base_size):
        ctypes.set_last_error(0)
        if not user32.SystemParametersInfoW(
            SPI_PRIVATE_SET_CURSOR_BASE_SIZE,
            0,
            ctypes.c_void_p(int(cursor_base_size)),
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
        ):
            error = ctypes.get_last_error()
            raise OSError(error, f"SystemParametersInfoW(0x2029, {cursor_base_size}) failed")

    def apply_stable_cursor_base_size(self):
        self.apply_cursor_base_size(STABLE_CURSOR_BASE_SIZE)

    def restore_default_cursor_base_size(self):
        self.apply_cursor_base_size(DEFAULT_CURSOR_BASE_SIZE)

    def cursor_output_dir(self):
        return Path(__file__).resolve().parent / "generated_cursors"

    def fallback_cursor_source_path(self, role):
        return Path(r"C:\Windows\Cursors") / FALLBACK_CURSOR_ROLES[role]

    def resolve_cursor_path(self, value):
        if not value:
            return None
        expanded = winreg.ExpandEnvironmentStrings(str(value))
        path = Path(expanded)
        return path if path.exists() else None

    def padded_cursor_path(self, role, source):
        extension = ".ani" if source.suffix.lower() == ".ani" else ".cur"
        return self.cursor_output_dir() / f"cursor_overlay_{role.lower()}{extension}"

    def ensure_padded_cursor_scheme(self):
        self.cursor_output_dir().mkdir(exist_ok=True)
        padded_paths = {}
        source_values = self.original_or_current_cursor_values()
        for role in FALLBACK_CURSOR_ROLES:
            source = self.resolve_cursor_path(source_values.get(role)) or self.fallback_cursor_source_path(role)
            target = self.padded_cursor_path(role, source)
            try:
                self.write_padded_cursor(source, target)
            except ValueError:
                fallback_source = self.fallback_cursor_source_path(role)
                if fallback_source == source:
                    raise
                target = self.padded_cursor_path(role, fallback_source)
                self.write_padded_cursor(fallback_source, target)
            padded_paths[role] = target
        return padded_paths

    def write_padded_cursor(self, source, target):
        data = source.read_bytes()
        if data[:4] == b"RIFF":
            target.write_bytes(self.build_padded_ani(data, source))
            return
        target.write_bytes(self.build_padded_cursor_from_data(data, source))

    def build_padded_cursor_from_data(self, data, source):
        image, hot_x, hot_y = self.read_best_cursor_frame(data, source, self.padded_glyph_size())
        canvas = QImage(PADDED_CURSOR_CANVAS_SIZE, PADDED_CURSOR_CANVAS_SIZE, QImage.Format_ARGB32)
        canvas.fill(Qt.transparent)

        painter = QPainter(canvas)
        painter.drawImage(0, 0, image)
        painter.end()

        png_data = self.image_to_png_bytes(canvas)
        return self.build_cursor_file(png_data, PADDED_CURSOR_CANVAS_SIZE, hot_x, hot_y)

    def read_best_cursor_frame(self, data, source, target_size):
        reserved = int.from_bytes(data[0:2], "little")
        cursor_type = int.from_bytes(data[2:4], "little")
        image_count = int.from_bytes(data[4:6], "little")
        if reserved != 0 or cursor_type != 2 or image_count <= 0:
            raise ValueError(f"Not a cursor file: {source}")

        entries = []
        for index in range(image_count):
            offset = 6 + index * 16
            width = data[offset] or 256
            height = data[offset + 1] or 256
            hot_x = int.from_bytes(data[offset + 4 : offset + 6], "little")
            hot_y = int.from_bytes(data[offset + 6 : offset + 8], "little")
            entries.append((width, height, hot_x, hot_y, index))

        width, height, hot_x, hot_y, index = min(
            entries,
            key=lambda item: (
                item[0] < target_size or item[1] < target_size,
                abs(item[0] - target_size) + abs(item[1] - target_size),
                item[0] * item[1],
            ),
        )
        byte_array = QByteArray(data)
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.ReadOnly)
        reader = QImageReader(buffer, b"cur")
        if not reader.jumpToImage(index):
            raise ValueError(f"Cannot select cursor frame {index}: {source}")
        image = reader.read()
        if image.isNull():
            raise ValueError(f"Cannot read cursor image: {source}: {reader.errorString()}")
        if image.width() != target_size or image.height() != target_size:
            original_width = image.width()
            original_height = image.height()
            image = image.scaled(
                target_size,
                target_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            hot_x = round(hot_x * image.width() / original_width)
            hot_y = round(hot_y * image.height() / original_height)
        return image.convertToFormat(QImage.Format_ARGB32), hot_x, hot_y

    def read_smallest_cursor_frame(self, data, source):
        return self.read_best_cursor_frame(data, source, 16)

    def build_padded_ani(self, data, source):
        if data[:4] != b"RIFF" or data[8:12] != b"ACON":
            raise ValueError(f"Not an animated cursor file: {source}")
        body = self.rebuild_ani_chunks(data, 12, len(data), source)
        return b"RIFF" + (len(body) + 4).to_bytes(4, "little") + b"ACON" + body

    def rebuild_ani_chunks(self, data, start, end, source):
        output = bytearray()
        offset = start
        while offset + 8 <= end:
            chunk_id = data[offset : offset + 4]
            chunk_size = int.from_bytes(data[offset + 4 : offset + 8], "little")
            chunk_start = offset + 8
            chunk_end = min(chunk_start + chunk_size, end)
            chunk_data = data[chunk_start:chunk_end]

            if chunk_id == b"icon":
                chunk_data = self.build_padded_cursor_from_data(chunk_data, source)
                chunk_size = len(chunk_data)
                output += chunk_id + chunk_size.to_bytes(4, "little") + chunk_data
            elif chunk_id in (b"RIFF", b"LIST") and len(chunk_data) >= 4:
                list_type = chunk_data[:4]
                nested = self.rebuild_ani_chunks(chunk_data, 4, len(chunk_data), source)
                rebuilt = list_type + nested
                output += chunk_id + len(rebuilt).to_bytes(4, "little") + rebuilt
                chunk_size = len(rebuilt)
            else:
                output += chunk_id + chunk_size.to_bytes(4, "little") + chunk_data

            if chunk_size & 1:
                output += b"\x00"
            offset = chunk_end + (int.from_bytes(data[offset + 4 : offset + 8], "little") & 1)
        return bytes(output)

    def extract_first_ani_cursor(self, data, source):
        offset = 12 if data[:4] == b"RIFF" else 0
        while offset + 8 <= len(data):
            chunk_id = data[offset : offset + 4]
            chunk_size = int.from_bytes(data[offset + 4 : offset + 8], "little")
            chunk_start = offset + 8
            chunk_end = chunk_start + chunk_size
            if chunk_id == b"icon":
                return data[chunk_start:chunk_end]
            if chunk_id in (b"RIFF", b"LIST"):
                nested = self.extract_first_ani_cursor(data[chunk_start + 4 : chunk_end], source)
                if nested:
                    return nested
            offset = chunk_end + (chunk_size & 1)
        raise ValueError(f"Animated cursor has no icon frame: {source}")

    def image_to_png_bytes(self, image):
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, "PNG")
        buffer.close()
        return bytes(byte_array)

    def build_cursor_file(self, png_data, size, hot_x, hot_y):
        width_byte = 0 if size >= 256 else size
        header = (0).to_bytes(2, "little") + (2).to_bytes(2, "little") + (1).to_bytes(2, "little")
        entry = bytes([width_byte, width_byte, 0, 0])
        entry += int(hot_x).to_bytes(2, "little")
        entry += int(hot_y).to_bytes(2, "little")
        entry += len(png_data).to_bytes(4, "little")
        entry += (22).to_bytes(4, "little")
        return header + entry + png_data

    def current_cursor_values(self):
        values = {"": self.get_registry_string(CURSORS_REGISTRY_PATH, "", "")}
        for role in FALLBACK_CURSOR_ROLES:
            values[role] = self.get_registry_string(CURSORS_REGISTRY_PATH, role, "")
        return values

    def save_original_cursor_values(self, values):
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, APP_REGISTRY_PATH, 0, winreg.KEY_ALL_ACCESS) as key:
            winreg.SetValueEx(key, ORIGINAL_CURSORS_VALUE, 0, winreg.REG_SZ, json.dumps(values))

    def is_current_padded_scheme(self):
        scheme_name = self.get_registry_string(CURSORS_REGISTRY_PATH, "", "")
        arrow = self.get_registry_string(CURSORS_REGISTRY_PATH, "Arrow", "")
        return scheme_name == PADDED_SCHEME_NAME or "generated_cursors" in arrow

    def saved_cursor_schemes(self):
        schemes = {}
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CURSORS_REGISTRY_PATH + r"\Schemes", 0, winreg.KEY_READ) as key:
                index = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    values = [item.strip() for item in str(value).split(",")]
                    scheme = {"": name}
                    for role, cursor_value in zip(SCHEME_ROLE_ORDER, values):
                        scheme[role] = cursor_value
                    schemes[name] = scheme
                    index += 1
        except FileNotFoundError:
            pass
        return schemes

    def set_source_cursor_scheme(self, name):
        schemes = self.saved_cursor_schemes()
        if name not in schemes:
            raise KeyError(f"Cursor scheme not found: {name}")
        self.save_original_cursor_values(schemes[name])

    def backup_current_cursor_scheme(self, force=False):
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, APP_REGISTRY_PATH, 0, winreg.KEY_ALL_ACCESS) as key:
            if not force:
                try:
                    winreg.QueryValueEx(key, ORIGINAL_CURSORS_VALUE)
                    return
                except FileNotFoundError:
                    pass
            winreg.SetValueEx(key, ORIGINAL_CURSORS_VALUE, 0, winreg.REG_SZ, json.dumps(self.current_cursor_values()))

    def original_or_current_cursor_values(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_REGISTRY_PATH, 0, winreg.KEY_READ) as key:
                raw_values, _ = winreg.QueryValueEx(key, ORIGINAL_CURSORS_VALUE)
            return json.loads(raw_values)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return self.current_cursor_values()

    def apply_padded_cursor_scheme(self):
        self.backup_current_cursor_scheme(force=not self.is_current_padded_scheme())
        padded_paths = self.ensure_padded_cursor_scheme()
        self.set_registry_string(CURSORS_REGISTRY_PATH, "", PADDED_SCHEME_NAME)
        for role in FALLBACK_CURSOR_ROLES:
            self.set_registry_string(CURSORS_REGISTRY_PATH, role, str(padded_paths[role]))
        self.reload_cursors()
        self.apply_stable_cursor_base_size()

    def apply_padded_cursor_scheme_from_saved_scheme(self, name):
        self.set_source_cursor_scheme(name)
        self.apply_padded_cursor_scheme()

    def apply_padded_cursor_scheme_with_glyph_size(self, glyph_size):
        self.set_padded_glyph_size(glyph_size)
        self.apply_padded_cursor_scheme()

    def restore_original_cursor_scheme(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_REGISTRY_PATH, 0, winreg.KEY_READ) as key:
                raw_values, _ = winreg.QueryValueEx(key, ORIGINAL_CURSORS_VALUE)
        except FileNotFoundError:
            return
        values = json.loads(raw_values)
        self.set_registry_string(CURSORS_REGISTRY_PATH, "", values.get("", ""))
        for role, value in values.items():
            if role:
                self.set_registry_string(CURSORS_REGISTRY_PATH, role, value)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_REGISTRY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, ORIGINAL_CURSORS_VALUE)
            except FileNotFoundError:
                pass
        self.reload_cursors()

    def restore_on_exit(self):
        self.restore_original_cursor_scheme()
        self.restore_default_cursor_base_size()

    def reload_cursors(self):
        user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, SPIF_SENDCHANGE)


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

        self.startup_action = QAction("Start with Windows")
        self.startup_action.setCheckable(True)
        self.startup_action.setChecked(self.startup_manager.is_enabled())
        self.startup_action.toggled.connect(self.set_startup_enabled)

        self.quit_action = QAction("Quit")
        self.quit_action.triggered.connect(self.quit)

        self.menu.addAction(self.status_action)
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

    def refresh_status(self):
        self.status_action.setText(self.pointer_rendering_manager.status_text())

    def quit(self):
        self.tray.hide()
        self.app.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    pointer_rendering_manager = PointerRenderingManager()
    pointer_rendering_manager.apply_padded_cursor_scheme()
    app.aboutToQuit.connect(pointer_rendering_manager.restore_on_exit)

    tray = QSystemTrayIcon(create_tray_icon())
    tray.setToolTip("Cursor Overlay")
    tray_controller = TrayController(app, tray, StartupManager(), pointer_rendering_manager)
    tray.show()

    app.tray_controller = tray_controller
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
