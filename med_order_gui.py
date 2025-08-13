import PySimpleGUI as sg
from collections import defaultdict
import csv
import re

sg.theme("SystemDefault")

# ── 解析工具：從檔案讀取「中文名稱」清單（去重、排序） ───────────────────────────
def load_medicines_from_file(file_path):
    names = set()
    chinese_pat = re.compile(r"[\u4e00-\u9fff]")

    def maybe_add(token):
        t = token.strip()
        if not t:
            return
        # 排除常見欄位名/標題
        bad_tokens = {"中文名稱", "英文名稱", "類別", "分類", "備註", "用途", "說明", "名稱"}
        if t in bad_tokens:
            return
        # 需包含中文字，且不是明顯的分類大標
        if not chinese_pat.search(t):
            return
        # 過濾像「麻醉與鎮痛劑」「疫苗與免疫診斷試劑」這類集合性大標（含「與」「及」「類」「藥物」「產品」但無劑型/商品名特徵）
        if re.fullmatch(r".{2,12}", t) and ("類" in t or "與" in t or "藥物" in t or "產品" in t):
            # 若你的資料確定所有條目都是產品名，可刪去這段判斷
            pass  # 保留；有些資料的大標也會被需要，可依實際資料再調
        names.add(t)

    # 嘗試用 csv/tsv 讀；若失敗改逐行切片
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            sample = f.read(2048)
            f.seek(0)
            delimiter = "\t" if ("\t" in sample and "," not in sample) else ","
            reader = csv.reader(f, delimiter=delimiter)
            header = next(reader, [])
            # 找「中文名稱」欄位；找不到就以「含中文字的第一欄」為準
            zh_idx = None
            for i, h in enumerate(header):
                if "中文" in h or "中文名稱" in h:
                    zh_idx = i
                    break
            if zh_idx is not None:
                maybe_add(header[zh_idx])  # 若標題就是名稱會被過濾掉
                for row in reader:
                    if zh_idx < len(row):
                        maybe_add(row[zh_idx])
            else:
                # 無明確表頭：遍歷每列，優先取第一個含中文的欄位
                f.seek(0)
                reader = csv.reader(f, delimiter=delimiter)
                for row in reader:
                    for cell in row:
                        if chinese_pat.search(cell):
                            maybe_add(cell)
                            break
    except Exception:
        # 非嚴格 csv：逐行處理，依據分隔符猜測
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if "\t" in line:
                    cells = line.split("\t")
                elif "," in line:
                    cells = line.split(",")
                else:
                    cells = [line]
                for cell in cells:
                    if chinese_pat.search(cell):
                        maybe_add(cell)
                        break

    # 去重 + 以字典序排序
    result = sorted(names)
    return result

# ── 狀態 ────────────────────────────────────────────────────────────────────
MEDICINES = []            # 將由「載入資料」按鈕或靜態清單填入
order = defaultdict(int)  # { 藥名: 數量 }
dirty = False             # 是否有未保存變更

# ── 輔助函式 ────────────────────────────────────────────────────────────────
def format_order_list(order_dict):
    return [f"{name} x {qty}" for name, qty in sorted(order_dict.items(), key=lambda x: x[0])]

def update_order_views(window, order_dict):
    window["-ORDER-"].update(format_order_list(order_dict))
    total_items = len(order_dict)
    total_qty = sum(order_dict.values())
    window["-SUMMARY-"].update(f"品項：{total_items}，總數量：{total_qty}")

def filter_medicines(query):
    q = query.strip()
    if not q:
        return MEDICINES
    return [m for m in MEDICINES if q in m]

# ── 介面配置 ────────────────────────────────────────────────────────────────
layout = [
    [sg.Text("請選擇藥品或輸入藥品名稱:")],
    [
        sg.Input(key="-INPUT-", enable_events=True, size=(24, 1)),
        sg.Button("查詢"),
        sg.Button("重置"),
        sg.Button("載入資料"),  # 新增：從你的檔案載入
    ],
    [
        sg.Listbox(values=MEDICINES, size=(32, 10),
                   key="-MEDICINE-", select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE)
    ],
    [
        sg.Text("數量:"),
        sg.Spin(values=list(range(1, 1001)), initial_value=1, size=(6, 1), key="-QTY-"),
        sg.Button("加入訂單", bind_return_key=True),
        sg.Button("刪除選中"),
        sg.Button("清空訂單"),
        sg.Button("取消")
    ],
    [sg.Text("訂單清單:", size=(40, 1))],
    [
        sg.Listbox(values=[], size=(48, 12), key="-ORDER-",
                   select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE)
    ],
    [
        sg.Button("保存TXT"),
        sg.Button("保存CSV"),
        sg.Text("品項：0，總數量：0", key="-SUMMARY-", pad=((20, 0), (0, 0)))
    ],
]

window = sg.Window("選藥系統（使用你的資料）", layout, finalize=True)

# ── 事件迴圈 ────────────────────────────────────────────────────────────────
while True:
    event, values = window.read()
    if event in (sg.WINDOW_CLOSED, "取消"):
        if dirty and sg.popup_yes_no("有未保存的變更，確定要離開嗎？") != "Yes":
            continue
        break

    # 立即查詢/即時過濾
    if event in ("查詢", "-INPUT-"):
        window["-MEDICINE-"].update(filter_medicines(values["-INPUT-"]))

    if event == "重置":
        window["-INPUT-"].update("")
        window["-MEDICINE-"].update(MEDICINES)

    # 載入你的資料檔
    if event == "載入資料":
        path = sg.popup_get_file(
            "選擇你的藥品資料檔（支援 TXT/CSV/TSV）",
            file_types=(("All", "*.*"), ("Text", "*.txt"), ("CSV", "*.csv"), ("TSV", "*.tsv")),
            no_window=True,
        )
        if path:
            try:
                loaded = load_medicines_from_file(path)
                if not loaded:
                    sg.popup("未在檔案中找到可用的『中文名稱』。請檢查格式或內容。")
                else:
                    MEDICINES = loaded  # 以你的資料覆蓋
                    window["-MEDICINE-"].update(MEDICINES)
                    sg.popup(f"已載入 {len(MEDICINES)} 筆項目。")
            except Exception as e:
                sg.popup(f"載入失敗：{e}")

    # 加入訂單
    if event == "加入訂單":
        try:
            qty = int(values["-QTY-"])
            if qty <= 0:
                raise ValueError
        except Exception:
            sg.popup("請輸入正確的數量！")
            continue

        selected = values["-MEDICINE-"]
        input_text = values["-INPUT-"].strip()

        if selected:
            for med in selected:
                order[med] += qty
            dirty = True
        elif input_text:
            order[input_text] += qty
            dirty = True
        else:
            sg.popup("請先選擇或輸入藥品！")
            continue

        update_order_views(window, order)
        window["-INPUT-"].update("")
        window["-MEDICINE-"].update(MEDICINES)

    # 刪除選中
    if event == "刪除選中":
        to_delete = values["-ORDER-"]
        if not to_delete:
            sg.popup("請先選擇要刪除的訂單項目！")
            continue

        if sg.popup_yes_no(f"確定刪除選中的 {len(to_delete)} 項？") != "Yes":
            continue

        for item in to_delete:
            name = item.split(" x ")[0]
            if name in order:
                del order[name]
                dirty = True

        update_order_views(window, order)

    # 清空訂單
    if event == "清空訂單":
        if order and sg.popup_yes_no("確定要清空整張訂單？") == "Yes":
            order.clear()
            dirty = True
            update_order_views(window, order)

    # 保存 TXT
    if event == "保存TXT":
        if not order:
            sg.popup("訂單為空，無法保存！")
            continue
        filename = sg.popup_get_file(
            "保存訂單為...",
            save_as=True,
            default_extension=".txt",
            file_types=(("Text Files", "*.txt"),),
            no_window=True,
        )
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("\n".join(format_order_list(order)))
                sg.popup(f"訂單已保存到 {filename}")
                dirty = False
            except Exception as e:
                sg.popup(f"保存失敗：{e}")

    # 保存 CSV
    if event == "保存CSV":
        if not order:
            sg.popup("訂單為空，無法保存！")
            continue
        filename = sg.popup_get_file(
            "保存訂單為...",
            save_as=True,
            default_extension=".csv",
            file_types=(("CSV Files", "*.csv"),),
            no_window=True,
        )
        if filename:
            try:
                with open(filename, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["藥品", "數量"])
                    for name, qty in sorted(order.items(), key=lambda x: x[0]):
                        writer.writerow([name, qty])
                sg.popup(f"訂單已保存到 {filename}")
                dirty = False
            except Exception as e:
                sg.popup(f"保存失敗：{e}")

window.close()