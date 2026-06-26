# Cursor Overlay

[English](README.md) | 繁體中文

Cursor Overlay 是一個 Windows 系統匣工具，用來測試是否能強制 Windows 避開會閃爍的一般游標渲染路徑。

這個 app 現在不建立任何 overlay 視窗、不自繪游標，也不隱藏或替換系統游標。它會測試一個未公開的 cursor base size runtime apply call，這個呼叫看起來比直接寫 registry 更接近 Windows Settings 改變指標大小時使用的路徑。

實用 workaround 是 padded cursor scheme：Windows 看到的是 `CursorBaseSize=144`，但 cursor 檔案本身是在 144 px 透明畫布上放一個 32 px 小圖形。這樣可以保留穩定渲染路徑，同時避免肉眼看到巨大游標。

## 背景

在 Windows 11 Insider Experimental build 26300.x 上，指標大小 1-7 會閃爍，有時還會變成半透明。指標大小改成 8 或以上後會立即停止閃爍，這強烈暗示 Windows 在這個門檻切換了游標渲染路徑。

本機測試顯示，表面的 `CursorSize` 數值不是關鍵 gate。只有 `CursorBaseSize` 至少為 `144` 時才會停止閃爍。

## 功能

- 只在 system tray 執行。
- 啟動時會產生並套用 padded small cursor scheme。
- 啟動時會自動套用 `CursorBaseSize=144`，但不改變 `CursorSize`。
- 可在不改變 `CursorSize` 的情況下套用 cursor base size preset：
  - `144`：穩定路徑。
  - `128`：低於門檻的對照值。
  - `32`：一般小 base size 對照值。
- 可恢復套用 padded scheme 前的原始 cursor scheme。
- 可從 Windows 已儲存的 cursor scheme 重新產生 padded scheme。
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

程式啟動後會出現在 system tray。右鍵點擊 tray icon 可開啟選單。啟動時會自動套用 padded cursor scheme 和穩定的 `CursorBaseSize=144` 路徑。

## System Tray 選單

- `Apply padded small cursor scheme`：產生 144 px cursor 檔案，內部放 32 px 小圖形，並套用為目前 cursor scheme。
- `Use saved cursor scheme`：選擇 Windows 已儲存的 cursor scheme 作為重新產生 padded cursor 的圖案來源。
- `Restore original cursor scheme`：恢復第一次套用 padded scheme 前備份的 cursor scheme。
- `Apply stable base size (144)`：在不改變 `CursorSize` 的情況下套用穩定的 `CursorBaseSize=144` 路徑。
- `Test below threshold (128)`：套用 `CursorBaseSize=128`。
- `Test unstable base size (32)`：套用 `CursorBaseSize=32`。
- `Start with Windows`：切換登入 Windows 後自動啟動。
- `Quit`：隱藏 tray icon，並結束程式。

啟用 `Start with Windows` 後，每次使用者登入時都會重新套用 padded cursor scheme 和穩定 base size。

## Runtime Apply Path

app 會保持 `CursorSize` 不變，接著呼叫：

```text
SystemParametersInfoW(0x2029, 0, IntPtr(CursorBaseSize), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
```

本機 probe 顯示，`0x2029` 搭配把 base size 整數直接放在 `pvParam` 可以即時更新 `CursorBaseSize`。傳入 `UINT` 指標是錯誤形式，會把指標地址寫進 registry。

## Padded Cursor Scheme

app 會先備份目前正在使用的 cursor scheme，然後從每個原始 cursor 檔案讀取最小 frame。接著把這個圖形放到 144 px 透明畫布左上角，保留原本 hotspot，並把產生的 `.cur` 寫到 `generated_cursors/`。

如果某個 cursor role 原本是空值或指向不存在的檔案，才會 fallback 到 `C:\Windows\Cursors` 底下對應的 Windows 預設 cursor。
如果原本是 `.ani` 動畫 cursor，會抽取其中第一個 cursor frame 轉成靜態 padded cursor。

這些檔案是 runtime output，已刻意加入 `.gitignore`，不會提交到 Git。

## 已測試結果

- 直接寫入任意 `CursorSize` 和 `CursorBaseSize` registry 組合不會改變 live cursor。
- `SPI_SETMOUSETRAILS(2)` 會即時生效並產生指標拖尾，但對閃爍沒有明顯幫助。它不是指標大小 8 觸發的同一條渲染路徑。
- `SystemParametersInfoW(0x2029, 0, IntPtr(baseSize), ...)` 會即時改變 `CursorBaseSize`。
- 前面的值不是關鍵：`7 / 144` 和 `8 / 144` 都會進入穩定狀態。
- 後面的值才是關鍵：`CursorBaseSize >= 144` 不會閃爍，低於 `144` 仍會閃爍。

## 注意事項

- 這是針對 Windows 游標合成 regression 的實驗性診斷 app。
- 它不建立 topmost overlay 視窗，因此不應阻止遊戲進入獨佔全螢幕。
