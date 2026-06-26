# Cursor Overlay

[English](README.md) | 繁體中文

Cursor Overlay 是一個 Windows 系統匣工具，用來測試是否能在不把指標大小改成實用性很低的 8 號外觀時，強制 Windows 避開會閃爍的一般游標渲染路徑。

這個 app 現在不建立任何 overlay 視窗、不自繪游標，也不隱藏或替換系統游標。它會測試一個未公開的 cursor base size runtime apply call，這個呼叫看起來比直接寫 registry 更接近 Windows Settings 改變指標大小時使用的路徑。

## 背景

在 Windows 11 Insider Experimental build 26300.x 上，指標大小 1-7 會閃爍，有時還會變成半透明。指標大小改成 8 或以上後會立即停止閃爍，這強烈暗示 Windows 在這個門檻切換了游標渲染路徑。

但指標大小 8 不適合日常使用，所以這個 app 測試是否能保留 `CursorSize=8`，同時透過 runtime cursor apply path 套用較小的 `CursorBaseSize`。

## 功能

- 只在 system tray 執行。
- 可套用三組 cursor path 測試 preset：
  - `1 / 32`：一般小游標 baseline。
  - `8 / 144`：已知穩定的大游標路徑。
  - `8 / 32`：小尺寸穩定候選路徑。
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

- `Apply size 1 baseline (1 / 32)`：寫入 `CursorSize=1` 並套用 `CursorBaseSize=32`。
- `Apply size 8 stable (8 / 144)`：寫入 `CursorSize=8` 並套用 `CursorBaseSize=144`。
- `Apply small stable candidate (8 / 32)`：寫入 `CursorSize=8` 並套用 `CursorBaseSize=32`。
- `Start with Windows`：切換登入 Windows 後自動啟動。
- `Quit`：隱藏 tray icon，並結束程式。

## Runtime Apply Path

app 會正常寫入 `CursorSize`，接著呼叫：

```text
SystemParametersInfoW(0x2029, 0, IntPtr(CursorBaseSize), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
```

本機 probe 顯示，`0x2029` 搭配把 base size 整數直接放在 `pvParam` 可以即時更新 `CursorBaseSize`。傳入 `UINT` 指標是錯誤形式，會把指標地址寫進 registry。

## 已測試結果

- 直接寫入任意 `CursorSize` 和 `CursorBaseSize` registry 組合不會改變 live cursor。
- `SPI_SETMOUSETRAILS(2)` 會即時生效並產生指標拖尾，但對閃爍沒有明顯幫助。它不是指標大小 8 觸發的同一條渲染路徑。
- `SystemParametersInfoW(0x2029, 0, IntPtr(baseSize), ...)` 會即時改變 `CursorBaseSize`，目前是最接近 Settings runtime apply 行為的候選方式。

## 注意事項

- 這是針對 Windows 游標合成 regression 的實驗性診斷 app。
- 它不建立 topmost overlay 視窗，因此不應阻止遊戲進入獨佔全螢幕。
