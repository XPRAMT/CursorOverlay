# Cursor Overlay

[English](README.md) | 繁體中文

Cursor Overlay 是一個 Windows system tray 小工具，用來處理 Windows 11
Insider Experimental 26300.x 的游標閃爍 regression。

目前確認有效的 workaround 是重啟 Desktop Window Manager (`dwm.exe`)。本機測試
顯示，從工作管理員手動停止 Desktop Window Manager 後，Windows 會自動重新啟動
DWM，游標閃爍會完全消失，直到下次關機或重新開機。

## 背景

在 Windows 11 Insider Experimental 26300.x 上，游標閃爍最早主要出現在 DXGI
Desktop Duplication 擷取路徑，而 Windows Graphics Capture 正常。到了
26300.8697，問題變嚴重，本機畫面上的游標也開始閃爍，但 WGC 擷取出來的游標仍然正常。

前面的測試曾發現 `CursorBaseSize >= 144` 可以避開會閃爍的路徑，但這個 workaround
會影響游標大小行為，也會牽涉 app 自訂游標。重啟 DWM 是比較乾淨的暫時解法，因為它直接重置壞掉的 compositor 狀態。

## 功能

- 只在 system tray 執行。
- 提供 `Restart Desktop Window Manager` tray action。
- 不建立 overlay 視窗。
- 不自繪、不隱藏、不替換、不縮放、不 hook 系統游標。
- 不修改 `CursorSize`、`CursorBaseSize` 或 cursor scheme。
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

- `Restart Desktop Window Manager`：要求系統管理員權限，然後對目前 Windows session 的 `dwm.exe` 執行 `taskkill`。Windows 會自動重新啟動 DWM。
- `Start with Windows`：切換登入 Windows 後自動啟動。
- `Quit`：隱藏 tray icon 並結束程式。

重啟 DWM 需要系統管理員權限，桌面也可能會短暫變黑或刷新，因為 Windows 正在重新啟動 compositor。app 啟動時不會自動重啟 DWM。

## 已測試結果

- DXGI Desktop Duplication 可能出現游標閃爍，但 WGC 正常。
- 在 26300.8697，本機游標也可能閃爍，但 WGC 擷取仍然正常。
- 指標大小 1-7 會受影響；指標大小 8 正常。
- 關鍵 size gate 看起來是 `CursorBaseSize >= 144`，不是 `CursorSize` 本身。
- 重啟 Desktop Window Manager 會完全清除閃爍狀態，直到下次關機或重新開機。

## 注意事項

這是針對 Windows compositor regression 的暫時 workaround，不是正式修復。向
Microsoft 回報時應該加入 DWM restart 這個發現，因為它指向 DWM cursor
composition state，而不只是 cursor 檔案內容問題。
