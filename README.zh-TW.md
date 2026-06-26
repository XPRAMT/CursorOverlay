# Cursor Overlay

[English](README.md) | 繁體中文

Cursor Overlay 是一個 Windows 系統匣工具，用來測試是否能在不把指標大小改成 8 的情況下，強制 Windows 避開會閃爍的一般游標渲染路徑。

這個 app 現在不建立任何 overlay 視窗、不自繪游標，也不隱藏或替換系統游標。它可以透過 `SPI_SETMOUSETRAILS(2)` 切換 Windows 最短有效 pointer trails runtime 設定，嘗試讓 Windows 使用不同的游標合成路徑。

## 背景

在 Windows 11 Insider Experimental build 26300.x 上，指標大小 1-7 會閃爍，有時還會變成半透明。指標大小改成 8 或以上後會立即停止閃爍，這強烈暗示 Windows 在這個門檻切換了游標渲染路徑。

但指標大小 8 不適合日常使用，所以這個 app 專注測試另一個可能的路徑切換方式：runtime pointer trails API。

## 功能

- 只在 system tray 執行。
- 可呼叫 `SPI_SETMOUSETRAILS(2)` 啟用 Windows 最短有效 pointer trails 設定。
- 修改前會備份原本的 `MouseTrails` 值。
- 停用選項時會恢復原值。
- 修改設定後會廣播 `WM_SETTINGCHANGE`。
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

- `Force software cursor path`：呼叫 `SPI_SETMOUSETRAILS(2)`。
- `Start with Windows`：切換登入 Windows 後自動啟動。
- `Quit`：隱藏 tray icon，並結束程式。

## Registry 變更

啟用 `Force software cursor path` 後，Windows 會收到：

```text
SPI_SETMOUSETRAILS(2)
```

原始 `MouseTrails` 值會備份在：

```text
HKCU\Software\CursorOverlay\OriginalMouseTrails
```

停用選項後，會恢復原本的值。

## 注意事項

- 這是針對 Windows 游標合成 regression 的實驗性 workaround。Windows 會把值 `1` 正規化回 `0`，而 `2` 是最短的有效 runtime 值，因此可能會看到短指標軌跡。
- 直接寫入任意 `CursorSize` 和 `CursorBaseSize` registry 組合不會改變 live cursor，所以已移除這些 tray preset。這個版本唯一確認能即時控制的是 `SPI_SETMOUSETRAILS`。
- 它不建立 topmost overlay 視窗，因此不應阻止遊戲進入獨佔全螢幕。
- 如果程式異常退出後設定仍保持啟用，重新執行 app 並取消 `Force software cursor path` 即可恢復。
