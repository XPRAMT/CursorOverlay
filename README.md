# Cursor Overlay

English | [繁體中文](README.zh-TW.md)

Cursor Overlay is a small Windows tray utility created to reduce cursor
flickering on affected Windows 11 builds. It keeps a transparent,
click-through, topmost overlay window following the system cursor. The app does
not draw its own cursor and does not hide or replace the Windows cursor.

It is written in Python with PySide6 and uses Win32 APIs for cursor position,
topmost positioning, and per-user startup registration.

## Background

This app was created to work around a cursor flickering issue on Windows 11
build 26300. The effective mitigation observed so far is keeping a transparent
topmost overlay around the live cursor position, which can change the desktop
composition path around the cursor without replacing the visible Windows cursor.

## Features

- Reads the live cursor position with `GetCursorInfo`.
- Keeps a transparent topmost overlay window following the cursor position.
- Can try forcing the normal-size cursor onto a different rendering path by
  enabling the hidden pointer-trails setting (`MouseTrails=-1`).
- Does not draw a custom cursor.
- Does not hide or replace the system cursor.
- Runs without a main window; management is done from the system tray.
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

- `Force software cursor path`: sets `MouseTrails=-1` and broadcasts the mouse
  setting change. This is intended to test whether size-1 cursors can avoid the
  flickering path without using pointer size 8.
- `Start with Windows`: toggles launch at user sign-in.
- `Quit`: stops the overlay, hides the tray icon, and exits.

## Startup Behavior

When `Start with Windows` is enabled, the app writes this per-user registry
value:

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run\CursorOverlay
```

The command uses `pythonw.exe` when available so startup does not open a console
window. Disabling the option removes the registry value.

## Notes

- This utility is Windows-only because it depends on Win32 cursor APIs.
- The overlay window is transparent, click-through, and topmost, so it should
  not intercept normal mouse input.
- `Force software cursor path` changes `HKCU\Control Panel\Mouse\MouseTrails`.
  The app stores the original value under `HKCU\Software\CursorOverlay` and
  restores it when the option is disabled.
