# Cursor Overlay

[English](README.md) | 繁體中文

Cursor Overlay 是一個為了減輕 Windows 11 游標閃爍問題而做的系統匣小工具。它會讓一個透明、click-through、最上層 overlay 視窗跟著系統游標移動。程式不自繪游標，也不隱藏或替換 Windows 系統游標。

這個工具使用 Python 與 PySide6 製作，並透過 Win32 API 讀取游標位置、維持最上層視窗，以及註冊目前使用者的開機自啟。

## 背景

這個 app 是為了解決 Windows 11 build 26300 的游標閃爍問題而誕生。目前觀察到有效的緩解方式，是在即時游標位置周圍維持透明最上層 overlay，藉此影響游標周圍的桌面合成路徑，而不是取代可見的 Windows 游標。

## 功能

- 使用 `GetCursorInfo` 讀取即時游標位置。
- 讓透明最上層 overlay 視窗跟隨游標位置。
- 可嘗試透過隱藏的 pointer trails 設定（`MouseTrails=-1`）強制一般大小游標走不同渲染路徑。
- 不自繪游標。
- 不隱藏或替換系統游標。
- 沒有主要視窗，完全透過 system tray 管理。
- 可選擇透過 Windows Run registry key 設定目前使用者的開機自啟。

## 需求

- Windows
- Python 3.10 或更新版本
- PySide6

安裝依賴：

```powershell
python -m pip install -r requirements.txt
```

## 執行

```powershell
python cursor_overlay.pyw
```

程式啟動後會出現在 system tray。右鍵點擊 tray icon 可開啟選單。

## System Tray 選單

- `Force software cursor path`：設定 `MouseTrails=-1` 並廣播滑鼠設定變更，用來測試 size 1 游標是否能不靠指標大小 8 就避開閃爍路徑。
- `Start with Windows`：切換登入 Windows 後自動啟動。
- `Quit`：停止 overlay、隱藏 tray icon，並結束程式。

## 開機自啟

啟用 `Start with Windows` 後，程式會寫入目前使用者的 registry 值：

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run\CursorOverlay
```

啟動命令會優先使用 `pythonw.exe`，避免開機啟動時出現 console 視窗。取消勾選後會移除這個 registry 值。

## 注意事項

- 這個工具只支援 Windows，因為它依賴 Win32 游標 API。
- 覆蓋層視窗是透明、click-through 且保持最上層，因此不會攔截一般滑鼠輸入。
- `Force software cursor path` 會修改 `HKCU\Control Panel\Mouse\MouseTrails`。程式會把原值備份到 `HKCU\Software\CursorOverlay`，停用選項時再恢復。
