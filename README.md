# Cursor Overlay

English | [繁體中文](README.zh-TW.md)

Cursor Overlay is a Windows tray utility for testing whether Windows can be
forced away from the flickering normal cursor rendering path without changing
the pointer size to 8.

The app no longer creates any overlay window, does not draw a cursor, and does
not hide or replace the system cursor. It only toggles the hidden pointer-trails
setting that may force Windows to use a different cursor composition path.

## Background

On Windows 11 Insider Experimental build 26300.x, pointer sizes 1-7 can flicker
and sometimes become semi-transparent. Pointer size 8 or higher stops the issue
immediately, which strongly suggests Windows switches cursor rendering paths at
that threshold.

Pointer size 8 is not practical for normal use, so this app focuses on another
possible path switch: `MouseTrails=-1`.

## Features

- Runs only in the system tray.
- Can set `HKCU\Control Panel\Mouse\MouseTrails` to `-1`.
- Can switch cursor-size registry presets from the tray:
  - `1 / 32`
  - `8 / 144`
  - `8 / 32`
  - `1 / 144`
- Backs up the original `MouseTrails` value before changing it.
- Restores the original value when the option is disabled.
- Broadcasts `WM_SETTINGCHANGE` after changing the setting.
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

- `Set size 1 (1 / 32)`: sets `CursorSize=1`, `CursorBaseSize=32`.
- `Set size 8 (8 / 144)`: sets `CursorSize=8`, `CursorBaseSize=144`.
- `Hybrid test (8 / 32)`: sets `CursorSize=8`, `CursorBaseSize=32`.
- `Hybrid test (1 / 144)`: sets `CursorSize=1`, `CursorBaseSize=144`.
- `Force software cursor path`: sets `MouseTrails=-1` and broadcasts the mouse
  setting change.
- `Start with Windows`: toggles launch at user sign-in.
- `Quit`: hides the tray icon and exits.

## Registry Changes

When `Force software cursor path` is enabled:

```text
HKCU\Control Panel\Mouse\MouseTrails = -1
```

The original value is stored here:

```text
HKCU\Software\CursorOverlay\OriginalMouseTrails
```

When the option is disabled, the original value is restored.

The cursor size presets modify:

```text
HKCU\SOFTWARE\Microsoft\Accessibility\CursorSize
HKCU\Control Panel\Cursors\CursorBaseSize
```

## Notes

- This is an experimental workaround for a Windows cursor composition
  regression.
- It does not create a topmost overlay window, so it should not block exclusive
  fullscreen games.
- If the setting remains enabled after an unexpected exit, run the app again and
  disable `Force software cursor path`.
