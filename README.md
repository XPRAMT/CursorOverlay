# Cursor Overlay

English | [繁體中文](README.zh-TW.md)

Cursor Overlay is a Windows tray utility for testing whether Windows can be
forced away from the flickering normal cursor rendering path.

The app no longer creates any overlay window, does not draw a cursor, and does
not hide or replace the system cursor. It tests an undocumented cursor-base-size
runtime apply call that appears to be closer to the path used when Windows
Settings changes the pointer size.

The practical workaround is a padded cursor scheme: Windows receives
`CursorBaseSize=144`, but the cursor files contain a small 32 px glyph on a
144 px transparent canvas. This keeps the stable rendering path while avoiding a
visually huge pointer.

## Background

On Windows 11 Insider Experimental build 26300.x, pointer sizes 1-7 can flicker
and sometimes become semi-transparent. Pointer size 8 or higher stops the issue
immediately, which strongly suggests Windows switches cursor rendering paths at
that threshold.

Local testing shows that the visible `CursorSize` value is not the decisive
gate. The flicker stops only when `CursorBaseSize` is at least `144`.

## Features

- Runs only in the system tray.
- Generates and applies a padded small cursor scheme at launch.
- Applies `CursorBaseSize=144` at launch without changing `CursorSize`.
- Can apply cursor-base-size presets without changing `CursorSize`:
  - `144`: stable path.
  - `128`: below-threshold comparison.
  - `32`: normal small-base comparison.
- Can restore the cursor scheme that was active before applying the padded
  scheme.
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
menu. On launch, it automatically applies the padded cursor scheme and the
stable `CursorBaseSize=144` path.

## Tray Menu

- `Apply padded small cursor scheme`: generates 144 px cursor files with a
  small 32 px glyph and applies them as the active cursor scheme.
- `Restore original cursor scheme`: restores the cursor scheme backed up before
  the padded scheme was first applied.
- `Apply stable base size (144)`: applies the stable `CursorBaseSize=144`
  path without changing `CursorSize`.
- `Test below threshold (128)`: applies `CursorBaseSize=128`.
- `Test unstable base size (32)`: applies `CursorBaseSize=32`.
- `Start with Windows`: toggles launch at user sign-in.
- `Quit`: hides the tray icon and exits.

When `Start with Windows` is enabled, the stable base size is applied again at
user sign-in, and the padded cursor scheme is re-applied.

## Runtime Apply Path

The app leaves `CursorSize` unchanged and calls:

```text
SystemParametersInfoW(0x2029, 0, IntPtr(CursorBaseSize), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
```

Local probing showed that `0x2029` with the base size passed as the `pvParam`
integer value can update `CursorBaseSize` live. Passing a pointer to a `UINT` is
wrong and can write the pointer address into the registry.

## Padded Cursor Scheme

The app reads the 32 px frame from standard Windows cursor files under
`C:\Windows\Cursors`, places it at the top-left of a 144 px transparent canvas,
preserves the original hotspot, and writes generated `.cur` files under
`generated_cursors/`.

Those generated files are runtime output and are intentionally ignored by Git.

## Tested Results

- Directly writing arbitrary `CursorSize` and `CursorBaseSize` registry
  combinations did not change the live cursor.
- `SPI_SETMOUSETRAILS(2)` does take effect at runtime and shows pointer trails,
  but it does not meaningfully reduce the flicker. It is not the same rendering
  path switch as pointer size 8.
- `SystemParametersInfoW(0x2029, 0, IntPtr(baseSize), ...)` does change
  `CursorBaseSize` live.
- The first value is not decisive: `7 / 144` and `8 / 144` both follow the
  stable behavior.
- The second value is decisive: `CursorBaseSize >= 144` does not flicker, while
  values below `144` still flicker.

## Notes

- This is an experimental diagnostic app for a Windows cursor composition
  regression.
- It does not create a topmost overlay window, so it should not block exclusive
  fullscreen games.
