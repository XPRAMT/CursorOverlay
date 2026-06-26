# Cursor Overlay

English | [繁體中文](README.zh-TW.md)

Cursor Overlay is a small Windows tray utility created to reduce cursor
flickering on affected Windows 11 builds. By default it keeps a transparent,
click-through, topmost overlay window following the system cursor. This can
change the desktop composition path around the cursor without replacing the
visible Windows cursor.

It is written in Python with PySide6 and uses Win32 APIs for cursor state,
cursor drawing, topmost positioning, and per-user startup registration.

## Background

This app was created to work around a cursor flickering issue on Windows 11
build 26300. The primary mitigation is not cursor replacement; it is keeping a
transparent topmost overlay around the live cursor position. Optional cursor
drawing and original-cursor hiding are kept as diagnostic controls.

## Features

- Reads the live cursor position with `GetCursorInfo`.
- Reads the active cursor style and hotspot with `CopyIcon` and `GetIconInfo`.
- Keeps a transparent topmost overlay window following the cursor position.
- Runs without a main window; management is done from the system tray.
- Can enable or disable an experimental self-drawn overlay cursor.
- Can hide or restore the original system cursor for testing by temporarily replacing
  Windows system cursors with transparent cursors.
- Temporarily restores the system cursor while the tray menu is open.
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

- `Draw overlay cursor`: enables or disables the self-drawn cursor overlay.
  This is off by default because the main flicker workaround does not require
  cursor replacement.
- `Hide original cursor`: hides or restores the original system cursor. This is
  independent from the overlay cursor, so disabling both can leave no visible
  cursor for testing.
- `Start with Windows`: toggles launch at user sign-in.
- `Quit`: stops the overlay, restores the system cursor, hides the tray icon,
  and exits.

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
- The overlay window is click-through and topmost, so it should not intercept
  normal mouse input.
- The app restores Windows system cursors when the tray menu opens and when the
  app exits. If it exits unexpectedly while the cursor is hidden, launching and
  quitting it again should restore the system cursor.
