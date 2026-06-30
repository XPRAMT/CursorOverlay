# Cursor Overlay

English | [繁體中文](README.zh-TW.md)

Cursor Overlay is a small Windows tray utility for a Windows 11 Insider
Experimental 26300.x cursor flicker regression.

The current workaround is to restart Desktop Window Manager (`dwm.exe`). Local
testing showed that manually stopping Desktop Window Manager from Task Manager
causes Windows to restart DWM, and the cursor flicker disappears until the next
shutdown or restart.

## Background

On Windows 11 Insider Experimental 26300.x, cursor flicker was first observed
through DXGI Desktop Duplication capture while Windows Graphics Capture stayed
normal. In build 26300.8697, the issue became worse: the local on-screen cursor
also started flickering, while WGC capture still showed a normal cursor.

Earlier tests found that `CursorBaseSize >= 144` could avoid the flickering
path, but that workaround affected cursor size behavior and app-specific
cursors. Restarting DWM is a cleaner temporary workaround because it resets the
bad compositor state directly.

## Features

- Runs only in the system tray.
- Provides a `Restart Desktop Window Manager` tray action.
- Does not create an overlay window.
- Does not draw, hide, replace, resize, or hook the system cursor.
- Does not change `CursorSize`, `CursorBaseSize`, or cursor schemes.
- Optional per-user startup launch through the Windows Run registry key.

## Requirements

- Windows
- Python 3.10 or newer
- PySide6

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Run

```powershell
python cursor_overlay.pyw
```

The application starts in the system tray. Right-click the tray icon to open the
menu.

## Tray Menu

- `Restart Desktop Window Manager`: asks for administrator approval, then runs
  `taskkill` against `dwm.exe` in the current Windows session. Windows
  automatically starts DWM again.
- `Start with Windows`: toggles launch at user sign-in.
- `Quit`: hides the tray icon and exits.

Restarting DWM requires administrator approval and can briefly blank or refresh
the desktop while Windows restarts the compositor. The app does not restart DWM
automatically on launch.

## Tested Results

- DXGI Desktop Duplication can show cursor flicker while WGC remains normal.
- In 26300.8697, the local cursor can also flicker while WGC capture remains
  normal.
- Pointer sizes 1-7 are affected; pointer size 8 is normal.
- The decisive size gate appeared to be `CursorBaseSize >= 144`, not
  `CursorSize` itself.
- Restarting Desktop Window Manager clears the flickering state completely until
  the next shutdown or restart.

## Notes

This is a temporary workaround for a Windows compositor regression, not a
permanent fix. The behavior should be reported to Microsoft with the DWM restart
finding because it points to DWM cursor composition state rather than cursor file
content alone.
