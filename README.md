# Cursor Overlay

English | [繁體中文](README.zh-TW.md)

Cursor Overlay is a Windows tray utility for testing whether Windows can be
forced away from the flickering normal cursor rendering path.

The app no longer creates any overlay window, does not draw a cursor, and does
not hide or replace the system cursor. It tests an undocumented cursor-base-size
runtime apply call that appears to be closer to the path used when Windows
Settings changes the pointer size.

The practical workaround is a padded cursor scheme: Windows receives
`CursorBaseSize=144`, but the cursor files contain a smaller glyph on a
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
- Restores the original cursor scheme and default `CursorBaseSize=32` when the
  app exits.
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

- `Use saved cursor scheme`: selects a saved Windows cursor scheme as the image
  source for regenerated padded cursors, or restores the Windows system default
  cursor source.
- `Glyph size`: regenerates the padded cursor scheme at a different visible
  glyph size. Larger values preserve more detail but look larger.
- `Start with Windows`: toggles launch at user sign-in.
- `Quit`: restores the original cursor scheme, restores `CursorBaseSize=32`,
  hides the tray icon, and exits.

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

The app first backs up the active cursor scheme, then reads the smallest frame
that best matches the selected glyph size from each original cursor file. It
places that glyph at the top-left of a 144 px transparent canvas, preserves the
original hotspot, and writes generated `.cur` or `.ani` files under
`generated_cursors/`. The default glyph size is `48` px.

If a cursor role was empty or points to a missing file, the app falls back to the
matching default cursor under `C:\Windows\Cursors`.
Animated `.ani` cursors are rebuilt as padded `.ani` files: the original RIFF
animation structure, frame rate, and frame sequence are preserved, while each
embedded cursor frame is converted to the 144 px padded format.

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
