# Cursor Overlay

[English](README.md) | 繁體中文

Cursor Overlay 是一個 Windows 系統匣小工具。它會讀取目前的系統游標位置與游標樣式，在相同螢幕位置繪製一個游標覆蓋層，並可在覆蓋層啟用時隱藏原始系統游標。

這個工具使用 Python 與 PySide6 製作，並透過 Win32 API 讀取游標狀態、繪製游標、維持最上層視窗，以及註冊目前使用者的開機自啟。

## 背景

這個 app 是為了解決 Windows 11 build 26300 的游標閃爍問題而誕生。它不取代 Windows 的游標系統，而是讀取即時游標狀態，將游標重畫成最上層覆蓋層，並可選擇隱藏原始游標。

## 功能

- 使用 `GetCursorInfo` 讀取即時游標位置。
- 使用 `CopyIcon` 與 `GetIconInfo` 讀取目前游標樣式與 hotspot。
- 使用 `DrawIconEx` 在原始游標位置繪製游標覆蓋層。
- 沒有主要視窗，完全透過 system tray 管理。
- 可從 system tray 選單啟用或停用自繪游標覆蓋層。
- 可從 system tray 選單隱藏或恢復原始系統游標；隱藏方式是暫時把 Windows system cursor 替換成透明游標。
- 開啟 system tray 選單時會暫時恢復系統游標。
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

- `Draw overlay cursor`：啟用或停用自繪游標覆蓋層。
- `Hide original cursor`：隱藏或恢復原始系統游標。這個開關與自繪游標互相獨立，因此停用自繪游標並維持隱藏原始游標時，可以進入完全沒有游標的測試狀態。
- `Start with Windows`：切換登入 Windows 後自動啟動。
- `Quit`：停止覆蓋層、恢復系統游標、隱藏 tray icon，並結束程式。

## 開機自啟

啟用 `Start with Windows` 後，程式會寫入目前使用者的 registry 值：

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run\CursorOverlay
```

啟動命令會優先使用 `pythonw.exe`，避免開機啟動時出現 console 視窗。取消勾選後會移除這個 registry 值。

## 注意事項

- 這個工具只支援 Windows，因為它依賴 Win32 游標 API。
- 覆蓋層視窗是 click-through 且保持最上層，因此不會攔截一般滑鼠輸入。
- 開啟 system tray 選單與程式正常退出時都會恢復 Windows system cursor。如果程式在游標被隱藏時異常退出，重新啟動並正常退出一次應可恢復系統游標。
