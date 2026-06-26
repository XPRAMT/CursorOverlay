# Cursor Overlay

[English](README.md) | 繁體中文

Cursor Overlay 是一個 Windows 系統匣工具，用來測試是否能強制 Windows 避開會閃爍的一般游標渲染路徑。

這個 app 現在不建立任何 overlay 視窗、不自繪游標，也不隱藏或替換系統游標。它會測試一個未公開的 cursor base size runtime apply call，這個呼叫看起來比直接寫 registry 更接近 Windows Settings 改變指標大小時使用的路徑。

## 背景

在 Windows 11 Insider Experimental build 26300.x 上，指標大小 1-7 會閃爍，有時還會變成半透明。指標大小改成 8 或以上後會立即停止閃爍，這強烈暗示 Windows 在這個門檻切換了游標渲染路徑。

本機測試顯示，表面的 `CursorSize` 數值不是關鍵 gate。只有 `CursorBaseSize` 至少為 `144` 時才會停止閃爍。

## 功能

- 只在 system tray 執行。
- 啟動時會自動套用 `CursorBaseSize=144`，但不改變 `CursorSize`。
- 可在不改變 `CursorSize` 的情況下套用 cursor base size preset：
  - `144`：穩定路徑。
  - `128`：低於門檻的對照值。
  - `32`：一般小 base size 對照值。
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

程式啟動後會出現在 system tray。右鍵點擊 tray icon 可開啟選單。啟動時會自動套用穩定的 `CursorBaseSize=144` 路徑。

## System Tray 選單

- `Apply stable base size (144)`：在不改變 `CursorSize` 的情況下套用穩定的 `CursorBaseSize=144` 路徑。
- `Test below threshold (128)`：套用 `CursorBaseSize=128`。
- `Test unstable base size (32)`：套用 `CursorBaseSize=32`。
- `Start with Windows`：切換登入 Windows 後自動啟動。
- `Quit`：隱藏 tray icon，並結束程式。

啟用 `Start with Windows` 後，每次使用者登入時都會重新套用穩定 base size。

## Runtime Apply Path

app 會保持 `CursorSize` 不變，接著呼叫：

```text
SystemParametersInfoW(0x2029, 0, IntPtr(CursorBaseSize), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
```

本機 probe 顯示，`0x2029` 搭配把 base size 整數直接放在 `pvParam` 可以即時更新 `CursorBaseSize`。傳入 `UINT` 指標是錯誤形式，會把指標地址寫進 registry。

## 已測試結果

- 直接寫入任意 `CursorSize` 和 `CursorBaseSize` registry 組合不會改變 live cursor。
- `SPI_SETMOUSETRAILS(2)` 會即時生效並產生指標拖尾，但對閃爍沒有明顯幫助。它不是指標大小 8 觸發的同一條渲染路徑。
- `SystemParametersInfoW(0x2029, 0, IntPtr(baseSize), ...)` 會即時改變 `CursorBaseSize`。
- 前面的值不是關鍵：`7 / 144` 和 `8 / 144` 都會進入穩定狀態。
- 後面的值才是關鍵：`CursorBaseSize >= 144` 不會閃爍，低於 `144` 仍會閃爍。

## 注意事項

- 這是針對 Windows 游標合成 regression 的實驗性診斷 app。
- 它不建立 topmost overlay 視窗，因此不應阻止遊戲進入獨佔全螢幕。
