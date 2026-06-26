# Cursor Overlay

English | [繁體中文](README.zh-TW.md)

Cursor Overlay is a Windows tray utility for testing whether Windows can be
forced away from the flickering normal cursor rendering path without changing
the pointer size to 8.

The app no longer creates any overlay window, does not draw a cursor, and does
not hide or replace the system cursor. The currently tested public toggles did
not reproduce the stable pointer-size-8 rendering path, so this version keeps a
tray-only diagnostic shell while the real runtime trigger is investigated.

## Background

On Windows 11 Insider Experimental build 26300.x, pointer sizes 1-7 can flicker
and sometimes become semi-transparent. Pointer size 8 or higher stops the issue
immediately, which strongly suggests Windows switches cursor rendering paths at
that threshold.

Pointer size 8 is not practical for normal use, so this app is used to test
possible path switches without introducing a topmost overlay window.

## Features

- Runs only in the system tray.
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

- `Start with Windows`: toggles launch at user sign-in.
- `Quit`: hides the tray icon and exits.

## Tested and Excluded

- Directly writing arbitrary `CursorSize` and `CursorBaseSize` registry
  combinations did not change the live cursor.
- `SPI_SETMOUSETRAILS(2)` does take effect at runtime and shows pointer trails,
  but it does not meaningfully reduce the flicker. It is not the same rendering
  path switch as pointer size 8.

## Notes

- This is an experimental diagnostic app for a Windows cursor composition
  regression.
- It does not create a topmost overlay window, so it should not block exclusive
  fullscreen games.
