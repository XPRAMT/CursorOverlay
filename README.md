# Cursor Overlay

Language: English | [繁體中文](README.zh-TW.md)

Cursor Overlay is a small Windows tray utility that reads the current system
cursor position and cursor style, draws a cursor overlay at the same screen
position, and can hide the original system cursor while the overlay is active.

It is written in Python with PySide6 and uses Win32 APIs for cursor state,
cursor drawing, topmost positioning, and per-user startup registration.

## Background

This app was created to work around a cursor flickering issue on Windows 11
build 26300. Instead of replacing the Windows cursor stack, it reads
the live cursor state, redraws the cursor as a topmost overlay, and optionally
hides the original cursor.

## Features

- Reads the live cursor position with `GetCursorInfo`.
- Reads the active cursor style and hotspot with `CopyIcon` and `GetIconInfo`.
- Draws the cursor overlay at the original cursor position with `DrawIconEx`.
- Runs without a main window; management is done from the system tray.
- Can hide or restore the original system cursor from the tray menu.
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
python cursor_overlay.py
```

The application starts in the system tray. Right-click the tray icon to open the
menu.

## Tray Menu

- `Hide original cursor`: hides or restores the original system cursor.
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
- If the app exits unexpectedly while the cursor is hidden, launching and
  quitting it again should restore the system cursor.
