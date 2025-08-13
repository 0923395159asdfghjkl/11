# 選藥系統 GUI

這是一個使用 PySimpleGUI 製作的簡易選藥/點單工具，可從你的資料檔（TXT/CSV/TSV）載入「中文名稱」清單，建立訂單並保存為 TXT/CSV。

## 需求
- Python 3.8+
- pip
- PySimpleGUI（已含於 `requirements.txt`）
- 注意：在 Linux 上需有 tkinter（`python3-tk` 系統套件）。若缺少可安裝：
  - Debian/Ubuntu: `sudo apt-get update && sudo apt-get install -y python3-tk`

## 安裝套件
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 執行
```bash
.venv/bin/python med_order_gui.py
```

## 使用提示
- 透過「載入資料」選擇你的 TXT/CSV/TSV 檔載入「中文名稱」。
- 可在輸入框即時過濾，選擇多筆後「加入訂單」。
- 訂單可刪除、清空，並保存為 TXT 或 CSV。

若在無桌面環境/遠端伺服器，請在本機具備 GUI 的環境執行本工具。