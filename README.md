# Cursor Overlay

English | [繁體中文](README.zh-TW.md)

Cursor Overlay is a Windows tray utility for testing whether Windows can be
forced away from the flickering normal cursor rendering path without changing
the pointer size to 8.

The app no longer creates any overlay window, does not draw a cursor, and does
not hide or replace the system cursor. It tests an undocumented cursor-base-size
runtime apply call that appears to be closer to the path used when Windows
Settings changes the pointer size.

## Background

On Windows 11 Insider Experimental build 26300.x, pointer sizes 1-7 can flicker
and sometimes become semi-transparent. Pointer size 8 or higher stops the issue
immediately, which strongly suggests Windows switches cursor rendering paths at
that threshold.

Pointer size 8 is not practical for normal use, so this app tests which
`CursorBaseSize` threshold is required after entering the size-8 cursor path.

## Features

- Runs only in the system tray.
- Can apply cursor-path threshold presets:
  - `1 / 32`: normal small pointer baseline.
  - `7 / 144`: gate test for whether `CursorSize` must be at least 8.
  - `8 / 144`: known stable large pointer path.
  - `8 / 32` through `8 / 128`: threshold tests.
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

- `Apply size 1 baseline (1 / 32)`: writes `CursorSize=1` and applies
  `CursorBaseSize=32`.
- `Gate test (7 / 144)`: writes `CursorSize=7` and applies `CursorBaseSize=144`.
- `Apply size 8 stable (8 / 144)`: writes `CursorSize=8` and applies
  `CursorBaseSize=144`.
- `Threshold test (8 / N)`: writes `CursorSize=8` and applies a test
  `CursorBaseSize` from `32` to `128`.
- `Start with Windows`: toggles launch at user sign-in.
- `Quit`: hides the tray icon and exits.

## Runtime Apply Path

The app writes `CursorSize` normally, then calls:

```text
SystemParametersInfoW(0x2029, 0, IntPtr(CursorBaseSize), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
```

Local probing showed that `0x2029` with the base size passed as the `pvParam`
integer value can update `CursorBaseSize` live. Passing a pointer to a `UINT` is
wrong and can write the pointer address into the registry.

## Tested Results

- Directly writing arbitrary `CursorSize` and `CursorBaseSize` registry
  combinations did not change the live cursor.
- `SPI_SETMOUSETRAILS(2)` does take effect at runtime and shows pointer trails,
  but it does not meaningfully reduce the flicker. It is not the same rendering
  path switch as pointer size 8.
- `SystemParametersInfoW(0x2029, 0, IntPtr(baseSize), ...)` does change
  `CursorBaseSize` live.
- `8 / 144` triggers the stable path and does not flicker.
- `8 / 32` still flickers, so `CursorSize=8` alone is not enough. The next test
  target is the minimum stable `CursorBaseSize`.

## Notes

- This is an experimental diagnostic app for a Windows cursor composition
  regression.
- It does not create a topmost overlay window, so it should not block exclusive
  fullscreen games.
