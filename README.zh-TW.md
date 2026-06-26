# Cursor Overlay

[English](README.md) | 繁體中文

Cursor Overlay 是一個 Windows 系統匣工具，用來測試是否能在不把指標大小改成 8 的情況下，強制 Windows 避開會閃爍的一般游標渲染路徑。

這個 app 現在不建立任何 overlay 視窗、不自繪游標，也不隱藏或替換系統游標。目前已測試的公開切換方式都沒有重現指標大小 8 的穩定渲染路徑，所以這個版本保留 system tray 診斷骨架，繼續追查真正的 runtime trigger。

## 背景

在 Windows 11 Insider Experimental build 26300.x 上，指標大小 1-7 會閃爍，有時還會變成半透明。指標大小改成 8 或以上後會立即停止閃爍，這強烈暗示 Windows 在這個門檻切換了游標渲染路徑。

但指標大小 8 不適合日常使用，所以這個 app 用來測試不依賴 topmost overlay 視窗的可能路徑切換方式。

## 功能

- 只在 system tray 執行。
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

- `Start with Windows`：切換登入 Windows 後自動啟動。
- `Quit`：隱藏 tray icon，並結束程式。

## 已測試並排除

- 直接寫入任意 `CursorSize` 和 `CursorBaseSize` registry 組合不會改變 live cursor。
- `SPI_SETMOUSETRAILS(2)` 會即時生效並產生指標拖尾，但對閃爍沒有明顯幫助。它不是指標大小 8 觸發的同一條渲染路徑。

## 注意事項

- 這是針對 Windows 游標合成 regression 的實驗性診斷 app。
- 它不建立 topmost overlay 視窗，因此不應阻止遊戲進入獨佔全螢幕。
