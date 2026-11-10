# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Menu
from tkinterdnd2 import DND_FILES, TkinterDnD
import pandas as pd
import networkx as nx
from pyvis.network import Network
import re
import os
import tempfile
import webbrowser
import threading
import datetime
import json
import traceback
import unicodedata
import time
import logging
import winreg
import subprocess
import sys

# --- ログ設定 ---
logging.basicConfig(level=logging.CRITICAL)

# --- 定数 ---
ERA_OFFSETS = {'M': 1868, 'T': 1912, 'S': 1926, 'H': 1989, 'R': 2019}

# --- ブラウザ起動ロジック ---
def open_url_securely(url):
    """
    Google Chromeがあればシークレットモードかつアプリモードで開く。
    なければデフォルトブラウザで開く。
    """
    chrome_path = None
    try:
        # レジストリからChromeのパスを探す
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as key:
            chrome_path = winreg.QueryValue(key, None)
    except:
        pass

    if chrome_path and os.path.exists(chrome_path):
        try:
            # --incognito: シークレットモード
            # --new-window: 新しいウィンドウで開く
            # --app=URL: アプリモード（アドレスバーなどを隠す）
            subprocess.Popen([chrome_path, '--incognito', '--new-window', f'--app={url}'])
            return
        except Exception:
            pass
            
    # フォールバック: 標準ブラウザ
    webbrowser.open(url)

# --- 文字変換・正規化ロジック ---

def hira_to_kata(text):
    """ひらがな -> 全角カタカナ変換"""
    kata = ""
    for c in text:
        if 0x3041 <= ord(c) <= 0x3096:
            kata += chr(ord(c) + 0x60)
        else:
            kata += c
    return kata

def normalize_text_unified(text):
    """検索用インデックスと検索クエリの両方で使う統一正規化関数"""
    if pd.isna(text): return ""
    text = str(text)
    text = unicodedata.normalize('NFKC', text)
    text = text.upper()
    # 検索用: 記号を除去して正規化
    text = re.sub(r'[−‐─━\-\(\)\.\/\s　]', '', text)
    return text

# --- 自然順ソート用キー関数 ---
def get_natural_sort_key(value):
    """文字列中の数値を数値として扱うためのキー"""
    text = str(value)
    return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', text)]

# --- 日付解析ロジック ---

def parse_fuzzy_date(query):
    """
    曖昧な数字列から日付候補リストを生成
    """
    candidates = []
    query_norm = unicodedata.normalize('NFKC', query).upper()
    
    # 1. 和暦パターン
    match_era = re.match(r'([MTSHR])\W?(\d{1,2})\W?(\d{1,2})\W?(\d{1,2})?', query_norm)
    if match_era:
        era, y, m, d = match_era.groups()
        y_west = ERA_OFFSETS[era] + int(y) - 1
        if d: candidates.append((y_west, int(m), int(d)))
        else: candidates.append((y_west, int(m), None))
        return candidates

    # 2. 数字のみ抽出
    nums = re.findall(r'\d+', query_norm)
    nums_joined = "".join(nums)
    if not nums_joined: return []
    
    L = len(nums_joined)
    val = int(nums_joined)
    
    # (A) そのまま年 (4桁)
    if L == 4 and 1900 <= val <= 2100:
        candidates.append((val, None, None))
        
    # (B) 分割パターン全探索
    # 2分割
    for i in range(1, L):
        p1 = nums_joined[:i]
        p2 = nums_joined[i:]
        v1, v2 = int(p1), int(p2)
        
        ys = []
        if len(p1) == 4 and 1900 <= v1 <= 2100: ys = [v1]
        elif len(p1) == 2: ys = [1900+v1, 2000+v1]
        
        if ys and 1 <= v2 <= 12:
            for y in ys: candidates.append((y, v2, None))
            
        if 1 <= v1 <= 12 and 1 <= v2 <= 31:
            candidates.append((None, v1, v2))

    # 3分割
    for i in range(1, L-1):
        for j in range(i+1, L):
            p1 = nums_joined[:i]
            p2 = nums_joined[i:j]
            p3 = nums_joined[j:]
            v1, v2, v3 = int(p1), int(p2), int(p3)
            
            ys = []
            if len(p1) == 4 and 1900 <= v1 <= 2100: ys = [v1]
            elif len(p1) == 2: ys = [1900+v1, 2000+v1]
            
            if ys and 1 <= v2 <= 12 and 1 <= v3 <= 31:
                for y in ys: candidates.append((y, v2, v3))

    return list(set(candidates))

def parse_excel_date(value):
    """Excel日付変換 (ソート用 & 表示変換用) - 強力パース版"""
    if pd.isna(value) or value == '': return None
    try:
        # 1. datetimeオブジェクトならそのまま
        if isinstance(value, (pd.Timestamp, datetime.datetime)):
            return value.to_pydatetime()
        if isinstance(value, datetime.date):
            return datetime.datetime(value.year, value.month, value.day)
        
        # 2. シリアル値判定
        val_float = None
        if isinstance(value, (int, float)):
            val_float = float(value)
        else:
            try:
                # 純粋な数値文字列かチェック ("1987.8.9"はここで弾かれる)
                if re.match(r'^\d+(\.\d+)?$', str(value).strip()):
                    val_float = float(str(value))
            except:
                pass
        
        if val_float is not None:
             if 1 <= val_float <= 100000:
                  return datetime.datetime(1899, 12, 30) + datetime.timedelta(days=val_float)

        # 3. 文字列解析 (1987.8.9, 1987/8/9, S62.8.9 等)
        s_raw = str(value).strip().upper()
        s_norm = unicodedata.normalize('NFKC', s_raw) # 半角化 (記号は残る)

        # 区切り文字 (., /, -, space) で分割して判定
        parts = re.split(r'[\.\-\/\s]+', s_norm)
        parts = [p for p in parts if p.isdigit()] # 数字部分のみ抽出
        
        if len(parts) == 3:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            # 年の補正 (2桁なら1900/2000年代)
            if y < 100: 
                y += 2000 if y < 30 else 1900
            
            if 1800 <= y <= 2200 and 1 <= m <= 12 and 1 <= d <= 31:
                return datetime.datetime(y, m, d)

        # 4. 和暦記号付きや8桁数字の解析
        s_clean = re.sub(r'[−‐─━\-\(\)\.\/\s　]', '', s_norm)
        
        # 和暦判定 (S500101)
        match_era = re.match(r'([MTSHR])\W?(\d{1,2})\W?(\d{1,2})\W?(\d{1,2})', s_clean)
        if match_era:
            era, y, m, d = match_era.groups()
            year = ERA_OFFSETS[era] + int(y) - 1
            return datetime.datetime(year, int(m), int(d))
        
        # 8桁数字 (19870809)
        if len(s_clean) == 8 and s_clean.isdigit():
            y = int(s_clean[:4])
            m = int(s_clean[4:6])
            d = int(s_clean[6:])
            if 1800 <= y <= 2200 and 1 <= m <= 12 and 1 <= d <= 31:
                return datetime.datetime(y, m, d)

    except:
        pass
    return None

def format_date_text(dt):
    """表示用日付文字列作成: 和暦(西暦)/月/日"""
    if pd.isna(dt): return ""
    try:
        y, m, d = dt.year, dt.month, dt.day
        era, ey = "", y
        if dt >= datetime.datetime(2019, 5, 1): era = "R"; ey = y - 2018
        elif dt >= datetime.datetime(1989, 1, 8): era = "H"; ey = y - 1988
        elif dt >= datetime.datetime(1926, 12, 25): era = "S"; ey = y - 1925
        elif dt >= datetime.datetime(1912, 7, 30): era = "T"; ey = y - 1911
        elif dt >= datetime.datetime(1868, 1, 25): era = "M"; ey = y - 1867
        else: return dt.strftime('%Y/%m/%d')
        return f"{era}{ey}({y})/{m:02}/{d:02}"
    except: return ""

def clean_referrer(text):
    if pd.isna(text): return None
    text = str(text)
    text = re.sub(r'[\(（].*?[\)）]', '', text)
    return text.strip()

def parse_fuzzy_date_query(query):
    return parse_fuzzy_date(query)

# --- HTMLテンプレート ---
def save_custom_graph(net, output_path, center_node):
    nodes_json = json.dumps(net.nodes, ensure_ascii=False)
    edges_json = json.dumps(net.edges, ensure_ascii=False)
    options_json = json.dumps(net.options, ensure_ascii=False)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <title>Customer Network</title>
    <link rel="stylesheet" href="https://unpkg.com/vis-network/standalone/umd/vis-network.min.css" type="text/css" />
    <style>
        body {{ margin: 0; padding: 0; background-color: #000000; color: #ffffff; font-family: 'Segoe UI', sans-serif; overflow: hidden; }}
        #mynetwork {{ width: 100vw; height: 100vh; border: none; }}
        .legend {{ position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.8); padding: 10px; border: 1px solid #444; pointer-events: none; z-index: 100; }}
        .legend div {{ margin-bottom: 5px; font-size: 14px; font-weight: bold; }}
        .legend span {{ display: inline-block; width: 12px; height: 12px; margin-right: 5px; }}
        div.vis-tooltip {{
            background-color: rgba(0, 0, 0, 0.9);
            color: #fff;
            border: 1px solid #00ff41;
            padding: 10px;
            font-size: 14px;
            border-radius: 5px;
            white-space: pre-wrap;
        }}
    </style>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    </head>
    <body>
    <div id="mynetwork"></div>
    <div class="legend">
        <div style="color:#ff0055"><span style="background:#ff0055"></span>中心人物 (Center)</div>
        <div style="color:#00ff41"><span style="background:#00ff41"></span>紹介者 (Upstream)</div>
        <div style="color:#00ccff"><span style="background:#00ccff"></span>被紹介者 (Downstream)</div>
        <div style="color:#aaaaaa"><span style="background:#aaaaaa"></span>グループ推測 (Group)</div>
    </div>
    <script type="text/javascript">
        var nodes = new vis.DataSet({nodes_json});
        var edges = new vis.DataSet({edges_json});
        var container = document.getElementById('mynetwork');
        var data = {{ nodes: nodes, edges: edges }};
        var options = {options_json};
        var network = new vis.Network(container, data, options);
        
        network.on("doubleClick", function (params) {{
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                navigator.clipboard.writeText(nodeId).then(function() {{
                    alert("【" + nodeId + "】をコピーしました。");
                }}, function(err) {{
                    alert("Selected: " + nodeId);
                }});
            }}
        }});
    </script>
    </body>
    </html>
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

class CustomerApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Customer Nexus System - Hyper Edition Final v45")
        self.geometry("1200x800")
        
        self.df = None
        self.current_indices = None
        self.last_loaded_path = None
        self.last_mod_time = None
        
        self.sort_col = None
        self.sort_asc = True
        self.selected_cols = []
        
        self.click_timer = None 
        self.last_click_time = 0
        self.last_click_col = None
        self.loading = False 

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview.Heading", font=("Meiryo UI", 9, "bold"), background="#333", foreground="white")
        style.configure("Treeview", font=("Meiryo UI", 10), rowheight=28)
        
        # 1. 上部エリア
        frame_top = tk.Frame(self, pady=10, bg="#111")
        frame_top.pack(fill=tk.X)
        
        self.btn_load = tk.Button(frame_top, text="📂 EXCEL読込", 
                                  command=self.start_load_excel, 
                                  bg="#00ff41", fg="black", font=("Meiryo UI", 11, "bold"), 
                                  width=15, relief="flat", cursor="hand2")
        self.btn_load.pack(side=tk.LEFT, padx=10)

        self.btn_reload = tk.Button(frame_top, text="↻ 再読込 (更新)", 
                                    command=self.reload_excel,
                                    bg="#87CEEB", fg="black", font=("Meiryo UI", 11, "bold"),
                                    width=15, relief="flat", cursor="hand2")
        # 読み込み完了後にpackする

        self.lbl_status = tk.Label(frame_top, text="ファイルをドロップしてください", 
                                   bg="#111", fg="#00ff41", font=("Meiryo UI", 11))
        self.lbl_status.pack(side=tk.LEFT, padx=10)

        frame_help = tk.Frame(frame_top, bg="#111")
        frame_help.pack(side=tk.RIGHT, padx=10)
        lbl_h1 = tk.Label(frame_help, text="━━━【項目名】━━━\n左クリック：検索対象化\n右クリック：並べ替え　", 
                          bg="#111", fg="#ffffff", font=("Meiryo UI", 8), justify=tk.LEFT)
        lbl_h1.pack(side=tk.LEFT, padx=10)
        lbl_h2 = tk.Label(frame_help, text="━━━【データ】━━━\nダブルクリック：関係図\n右クリック：複数行選択", 
                          bg="#111", fg="#ffffff", font=("Meiryo UI", 8), justify=tk.LEFT)
        lbl_h2.pack(side=tk.LEFT, padx=10)

        self.progress = ttk.Progressbar(frame_top, orient="horizontal", length=300, mode="indeterminate")
        
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.on_drop)

        # 2. 検索エリア
        frame_search = tk.LabelFrame(self, text="検索", pady=8, padx=8, font=("Meiryo UI", 11, "bold"), bg="#f0f0f0")
        frame_search.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(frame_search, text="キーワード:", font=("Meiryo UI", 11), bg="#f0f0f0").pack(side=tk.LEFT)
        self.entry_search = tk.Entry(frame_search, width=30, font=("Meiryo UI", 12))
        self.entry_search.pack(side=tk.LEFT, padx=8)
        self.entry_search.bind('<Return>', lambda e: self.run_search_new()) 
        
        btn_search = tk.Button(frame_search, text="🔍 新規検索", command=lambda: self.run_search_new(), 
                               bg="#E91E63", fg="white", font=("Meiryo UI", 10, "bold"), width=10)
        btn_search.pack(side=tk.LEFT, padx=5)

        btn_filter = tk.Button(frame_search, text="🔍 絞り込み", command=lambda: self.run_search_filter(), 
                               bg="#FF9800", fg="white", font=("Meiryo UI", 10, "bold"), width=10)
        btn_filter.pack(side=tk.LEFT, padx=5)
        
        tk.Label(frame_search, text="|", bg="#f0f0f0", fg="#aaa").pack(side=tk.LEFT, padx=5)
        
        btn_name = tk.Button(frame_search, text="登録名", command=lambda: self.set_cols_and_search(['登録名', '旧登録名']), 
                             bg="#2196F3", fg="white", font=("Meiryo UI", 9))
        btn_name.pack(side=tk.LEFT, padx=2)
        
        btn_birth = tk.Button(frame_search, text="誕生日", command=lambda: self.set_cols_and_search(['生年月日'], sort_by_birth=True), 
                              bg="#2196F3", fg="white", font=("Meiryo UI", 9))
        btn_birth.pack(side=tk.LEFT, padx=2)
        
        btn_tel = tk.Button(frame_search, text="電話番号", command=lambda: self.set_cols_and_search(['電話番号', '電話番号2', '電話番号3']), 
                            bg="#2196F3", fg="white", font=("Meiryo UI", 9))
        btn_tel.pack(side=tk.LEFT, padx=2)
        
        btn_reset = tk.Button(frame_search, text="リセット", command=self.reset_search, bg="#666", fg="white")
        btn_reset.pack(side=tk.LEFT, padx=10)
        
        self.lbl_selected_cols = tk.Label(frame_search, text="", bg="#FFE4B5", font=("Meiryo UI", 9))
        self.lbl_selected_cols.pack(side=tk.LEFT, padx=15)

        # 3. リスト
        frame_list = tk.Frame(self)
        frame_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tree = ttk.Treeview(frame_list, show='headings', selectmode='extended') 
        v_bar = ttk.Scrollbar(frame_list, orient=tk.VERTICAL, command=self.tree.yview)
        h_bar = ttk.Scrollbar(frame_list, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=v_bar.set, xscroll=h_bar.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_bar.grid(row=0, column=1, sticky='ns')
        h_bar.grid(row=1, column=0, sticky='ew')
        
        frame_list.grid_rowconfigure(0, weight=1)
        frame_list.grid_columnconfigure(0, weight=1)
        
        # --- イベントバインド ---
        self.tree.bind("<Button-1>", self.on_header_click)
        self.tree.bind("<Button-3>", self.on_header_right_click)
        self.tree.bind("<Double-1>", self.on_item_double_click)
        
        self.root = self.winfo_toplevel()
        self.root.bind("<Control-c>", self.copy_selection)
        
        self.check_file_update()

    def check_file_update(self):
        if self.last_loaded_path:
            try:
                if not os.path.exists(self.last_loaded_path):
                    self.btn_reload.config(bg="#A9A9A9", text="ファイル不明", state=tk.DISABLED)
                else:
                    current_mtime = os.path.getmtime(self.last_loaded_path)
                    if self.last_mod_time and current_mtime > self.last_mod_time:
                        self.btn_reload.config(bg="#FF4500", text="再読込 (更新あり!)", fg="white")
                    else:
                        if self.btn_reload.cget('bg') != "#FF4500":
                            self.btn_reload.config(bg="#87CEEB", text="再読込 (更新)", state=tk.NORMAL, fg="black")
            except Exception:
                pass
        self.after(2000, self.check_file_update)

    def on_drop(self, event):
        try:
            path = event.data.replace('{', '').replace('}', '')
            if path.endswith('.xlsx'): self.process_load(path)
        except Exception as e:
            messagebox.showerror("Error", f"ドロップ処理エラー: {e}")

    def start_load_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx")])
        if path: self.process_load(path)

    def reload_excel(self):
        if self.last_loaded_path and os.path.exists(self.last_loaded_path):
            self.process_load(self.last_loaded_path)
        else:
            messagebox.showerror("エラー", "再読み込みするファイルが見つかりません。")

    def process_load(self, file_path):
        if hasattr(self, 'loading') and self.loading: return
        self.loading = True
        self.btn_load.config(state=tk.DISABLED)
        if self.btn_reload.winfo_ismapped():
            self.btn_reload.config(state=tk.DISABLED)
            
        self.lbl_status.config(text="データ読み込み中...", fg="#00ff41")
        self.progress.pack(side=tk.LEFT, padx=10)
        self.progress.start(10)
        threading.Thread(target=self.load_thread, args=(file_path,), daemon=True).start()

    def load_thread(self, path):
        try:
            if not os.path.exists(path):
                raise FileNotFoundError(f"ファイルが見つかりません: {path}")

            try:
                df = pd.read_excel(path, dtype=object)
            except PermissionError:
                raise PermissionError("ファイルが開かれているか、アクセス権限がありません。\nExcelを閉じてから再試行してください。")
            except Exception as e:
                raise Exception(f"Excel読み込みエラー: {e}")

            df = df.fillna('')
            
            required = ['登録名']
            for col in required:
                if col not in df.columns: raise Exception(f"必須列「{col}」不足")

            if '本名' in df.columns:
                mask = (df['登録名'] == '') & (df['本名'] == '')
                df = df[~mask].reset_index(drop=True)
            
            birth_col_dates = None
            if '生年月日' in df.columns:
                birth_col_dates = df['生年月日'].apply(parse_excel_date)
                
                def format_date_row(val, dt):
                    if pd.notna(dt):
                        return format_date_text(dt)
                    return str(val) if val != '' else ''
                
                df['生年月日'] = [format_date_row(v, d) for v, d in zip(df['生年月日'], birth_col_dates)]

            df = df.astype(str)
            
            if birth_col_dates is not None:
                df['__sort_birth__'] = birth_col_dates

            for col in df.columns:
                if col.startswith('__'): continue
                if col != '生年月日': 
                    df[f'__sk_{col}'] = df[col].apply(get_natural_sort_key)

            def make_index(row):
                vals = [str(val) for col, val in row.items() 
                        if not col.startswith('__') and col != '生年月日']
                return normalize_text_unified(' '.join(vals))
            
            df['search_index'] = df.apply(make_index, axis=1)
            
            if '紹介者' in df.columns:
                df['__clean_referrer__'] = df['紹介者'].apply(clean_referrer)

            self.after(0, self.load_success, df, path)
            
        except Exception as e:
            err_detail = traceback.format_exc()
            self.after(0, self.load_failed, str(e), err_detail)

    def load_success(self, df, path):
        self.df = df
        self.current_indices = df.index
        self.last_loaded_path = path
        try:
            self.last_mod_time = os.path.getmtime(path)
        except:
            self.last_mod_time = time.time()
        
        self.loading = False
        self.progress.stop()
        self.progress.pack_forget()
        self.btn_load.config(state=tk.NORMAL)
        
        self.btn_reload.pack(side=tk.LEFT, padx=10)
        self.btn_reload.config(bg="#87CEEB", text="再読込 (更新)", state=tk.NORMAL, fg="black")
        
        self.lbl_status.config(text=f"✅ 読込完了: {len(df)}件\n{os.path.basename(path)}", fg="#00ff41")
        
        self.sort_col = None
        self.sort_asc = True
        
        # 列幅設定 (ご指示の内容)
        disp_cols = [c for c in df.columns if not c.startswith('__') and c != 'search_index']
        self.tree['columns'] = disp_cols
        for c in disp_cols:
            self.tree.heading(c, text=c)
            width = 100
            
            if c == '会員ID': width = 50
            elif c in ['登録名', 'フリガナ', '旧登録名', '本名']: width = 120
            elif c == '生年月日': width = 170
            elif '電話番号' in c: width = 150
            elif c == '住所': width = 340
            elif c == '備考': width = 300
            elif c in ['紹介者', 'グループ']: width = 100
            elif c in ['記入者', 'アナウンス可能(時間帯)', 'チケット欄', '身分証1', '身分証2', '身分証チェック']: width = 50
            
            self.tree.column(c, width=width)
            
        self.update_list()

    def load_failed(self, msg, detail):
        self.loading = False
        self.progress.stop()
        self.progress.pack_forget()
        self.btn_load.config(state=tk.NORMAL)
        if self.btn_reload.winfo_ismapped():
            self.btn_reload.config(state=tk.NORMAL)
        
        self.lbl_status.config(text="読込エラー発生", fg="red")
        
        win = tk.Toplevel(self)
        win.title("Error")
        win.geometry("600x400")
        lbl = tk.Label(win, text="読み込みに失敗しました。\n以下の内容を確認してください。", fg="red")
        lbl.pack(pady=5)
        txt = tk.Text(win, wrap=tk.WORD)
        txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        txt.insert(tk.END, f"{msg}\n\n=== Traceback ===\n{detail}")
        txt.config(state=tk.DISABLED)

    # --- クリック処理 ---
    def on_header_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "heading":
            col_id = self.tree.identify_column(event.x)
            col_name = self.tree.column(col_id, "id")
            if col_name in self.selected_cols:
                self.selected_cols.remove(col_name)
            else:
                self.selected_cols.append(col_name)
            self.update_heading_display()
            self.run_search_new(apply_sort=False)

    def on_header_right_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "heading":
            col_id = self.tree.identify_column(event.x)
            col_name = self.tree.column(col_id, "id")
            if self.sort_col == col_name:
                if self.sort_asc is True: self.sort_asc = False
                elif self.sort_asc is False:
                    self.sort_col = None; self.sort_asc = True
                else: self.sort_asc = True 
            else:
                self.sort_col = col_name; self.sort_asc = True
            self.run_single_sort()
        elif region == "cell":
            row_id = self.tree.identify_row(event.y)
            if row_id:
                sel = list(self.tree.selection())
                if row_id not in sel:
                    sel.append(row_id)
                    self.tree.selection_set(sel)

    def update_heading_display(self):
        for col in self.tree["columns"]:
            text = col
            if self.sort_col == col: text += " ▲" if self.sort_asc else " ▼"
            if col in self.selected_cols: text = f"☑ {text}"
            self.tree.heading(col, text=text)
        if self.selected_cols:
            text = "検索対象: " + " , ".join(self.selected_cols)
            self.lbl_selected_cols.config(text=text, bg="#FFE4B5")
        else:
            self.lbl_selected_cols.config(text="検索対象: 全列", bg="#f0f0f0")

    # --- 検索・ソート ---
    def set_cols_and_search(self, cols, sort_by_birth=False):
        if self.df is None: return
        valid_cols = [c for c in cols if c in self.df.columns]
        self.selected_cols = valid_cols
        self.update_heading_display()
        if sort_by_birth:
            self.sort_col = '生年月日'; self.sort_asc = True
            self.run_search_new(apply_sort=True)
        else:
            self.run_search_new(apply_sort=False)

    def get_search_mask(self, source_indices):
        if self.df is None: return None
        query = self.entry_search.get()
        if not query.strip() and not self.selected_cols:
            return pd.Series([True] * len(source_indices), index=source_indices)

        q_norm_base = normalize_text_unified(query)
        q_kana_conv = normalize_text_unified(hira_to_kata(query))
        target_dates = parse_fuzzy_date(query)

        subset = self.df.loc[source_indices]
        mask = pd.Series([False] * len(subset), index=subset.index)

        if q_norm_base:
            if self.selected_cols:
                valid_cols = [c for c in self.selected_cols if c in self.df.columns]
                if valid_cols:
                    def make_temp_index(row):
                        txt = ' '.join(row[valid_cols].astype(str).values)
                        return normalize_text_unified(txt)
                    temp_index = subset.apply(make_temp_index, axis=1)
                    mask = mask | temp_index.str.contains(q_norm_base, na=False, regex=False)
                    if q_kana_conv != q_norm_base:
                        mask = mask | temp_index.str.contains(q_kana_conv, na=False, regex=False)
            else:
                mask = mask | subset['search_index'].str.contains(q_norm_base, na=False, regex=False)
                if q_kana_conv != q_norm_base:
                    mask = mask | subset['search_index'].str.contains(q_kana_conv, na=False, regex=False)

        do_date_search = True
        if self.selected_cols and '生年月日' not in self.selected_cols: do_date_search = False
        if do_date_search and target_dates and '__sort_birth__' in self.df.columns:
            def check_date_match(dt):
                if pd.isna(dt): return False
                if not isinstance(dt, (datetime.datetime, pd.Timestamp, datetime.date)): return False
                for (y, m, d) in target_dates:
                    match = True
                    if y is not None and dt.year != y: match = False
                    if m is not None and dt.month != m: match = False
                    if d is not None and dt.day != d: match = False
                    if match: return True
                return False
            date_mask = subset['__sort_birth__'].apply(check_date_match)
            mask = mask | date_mask

        if not query.strip():
            mask = pd.Series([True] * len(subset), index=subset.index)
        return mask

    def run_search_new(self, apply_sort=False):
        if self.df is None: return
        mask = self.get_search_mask(self.df.index)
        self.current_indices = self.df.index[mask]
        
        if apply_sort and '__sort_birth__' in self.df.columns:
            self.sort_col = '生年月日'; self.sort_asc = True
            self.run_single_sort()
        else:
            if self.sort_col: self.run_single_sort()
            else: self.update_list()
        self.update_status_msg("新規検索結果")

    def run_search_filter(self):
        if self.df is None: return
        mask = self.get_search_mask(self.current_indices)
        self.current_indices = self.current_indices[mask]
        if self.sort_col: self.run_single_sort()
        else: self.update_list()
        self.update_status_msg("絞り込み結果")

    def run_single_sort(self):
        if self.df is None or len(self.current_indices) == 0:
            self.update_list(); self.update_heading_display(); return
        
        if not self.sort_col:
            self.current_indices = self.current_indices.sort_values()
            self.update_heading_display(); self.update_list()
            self.lbl_status.config(text="ソート解除", fg="#00ffff")
            return

        try:
            subset = self.df.loc[self.current_indices]
            target = self.sort_col
            if self.sort_col == '生年月日' and '__sort_birth__' in self.df.columns: target = '__sort_birth__'
            elif f'__sk_{self.sort_col}' in self.df.columns: target = f'__sk_{self.sort_col}'
            
            sorted_indices = subset.sort_values(by=target, ascending=self.sort_asc, na_position='last').index
            self.current_indices = sorted_indices
            self.update_heading_display(); self.update_list()
            state_text = '昇順' if self.sort_asc else '降順'
            self.lbl_status.config(text=f"ソート: {self.sort_col} [{state_text}]", fg="#00ffff")
        except Exception as e:
            traceback.print_exc()
            self.lbl_status.config(text="ソートエラー", fg="red")

    def update_status_msg(self, prefix):
        msg = f"{prefix}: {len(self.current_indices)}件"
        if self.selected_cols: msg += f" (対象: {','.join(self.selected_cols)})"
        self.lbl_status.config(text=msg, fg="orange")

    def copy_selection(self, event):
        selected_items = self.tree.selection()
        if not selected_items: return
        copy_text = ""
        for item in selected_items:
            vals = self.tree.item(item, "values")
            copy_text += "\t".join([str(v) for v in vals]) + "\n"
        self.root.clipboard_clear()
        self.root.clipboard_append(copy_text)
        self.lbl_status.config(text=f"コピー: {len(selected_items)}行", fg="green")

    def reset_search(self):
        self.entry_search.delete(0, tk.END)
        self.selected_cols = []
        self.sort_col = None
        self.update_heading_display()
        if self.df is not None:
            self.current_indices = self.df.index.sort_values()
            self.update_list()
        self.lbl_status.config(text=f"全件表示", fg="black")

    def update_list(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        if self.df is None: return
        disp_cols = self.tree['columns']
        count = 0
        limit = 5000 
        for idx in self.current_indices:
            if count >= limit: break
            row = self.df.loc[idx]
            vals = [row[c] for c in disp_cols]
            self.tree.insert('', tk.END, values=vals, iid=str(idx))
            count += 1
        if len(self.current_indices) > limit:
            self.lbl_status.config(text=f"{self.lbl_status.cget('text')} (表示制限:先頭{limit}件)", fg="red")

    def on_item_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell": return
        item_id = self.tree.focus()
        if not item_id: return
        idx = int(item_id)
        name = self.df.loc[idx, '登録名']
        if name: self.generate_graph(name)

    def generate_graph(self, center_person):
        try:
            self.config(cursor="wait")
            G = nx.DiGraph()
            valid_names = set(str(n).strip() for n in self.df['登録名'].unique() if pd.notna(n) and str(n).strip())
            
            for idx, row in self.df.iterrows():
                target = None 
                u = str(row['登録名']).strip()
                if not u: continue
                ref_raw = row.get('__clean_referrer__', '')
                if pd.isna(ref_raw): ref_raw = ''
                ref = str(ref_raw).strip()
                grp_raw = row.get('グループ', '')
                if pd.isna(grp_raw): grp_raw = ''
                grp = str(grp_raw).strip()
                
                info_list = []
                for k, v in row.items():
                    if not k.startswith('__') and k not in ['search_index', 'clean_referrer']:
                        info_list.append(f"{k}: {v}")
                info = "\n".join(info_list)
                
                G.add_node(u, title=info, group=grp)
                
                if ref:
                    if ref in valid_names and ref != u: target = ref
                    else:
                        if grp in valid_names and grp != u: target = grp
                        else:
                            target = ref
                            if target not in G: G.add_node(target, title="※該当登録名なし", group="UnknownNode", shape='box', color='#999999')
                elif grp:
                    if grp in valid_names and grp != u: target = grp
                    else:
                        target = grp
                        if target not in G: G.add_node(target, title="グループ名", group="GroupNode", shape='box', color='#aaaaaa')
                if target: G.add_edge(target, u)

            if center_person not in G:
                messagebox.showwarning("Info", "データなし")
                return

            sub_nodes = nx.ego_graph(G.to_undirected(), center_person, radius=8).nodes()
            sub_G = G.subgraph(sub_nodes)
            net = Network(height='100%', width='100%', bgcolor='#000000', font_color='white', directed=True)
            net.from_nx(sub_G)
            
            for node in net.nodes:
                nid = node['id']
                node['shape'] = 'box'
                node['font'] = {'size': 20, 'color': '#ffffff', 'face': 'Meiryo UI'}
                node['borderWidth'] = 2
                node['shadow'] = True
                
                group = node.get('group')
                if group == 'GroupNode': node['color'] = {'background': 'rgba(100,100,100,0.8)', 'border': '#aaaaaa'}; continue
                if group == 'UnknownNode': node['color'] = {'background': 'rgba(150,50,50,0.8)', 'border': '#ff0000'}; continue

                if nid == center_person: node['color'] = {'background': 'rgba(255,0,80,0.7)', 'border': '#ff0055'}; node['font']['size'] = 30
                elif nid in list(G.predecessors(center_person)): node['color'] = {'background': 'rgba(0,255,65,0.6)', 'border': '#00ff41'}
                elif any(center_person in list(G.successors(p)) for p in G.predecessors(nid)): node['color'] = {'background': 'rgba(255,165,0,0.6)', 'border': '#ffa500'}
                else: node['color'] = {'background': 'rgba(0,204,255,0.6)', 'border': '#00ccff'}

            for edge in net.edges:
                edge['color'] = {'color': '#666666', 'opacity': 0.6}; edge['width'] = 1; edge['smooth'] = False 

            net.set_options("""
            var options = {
              "physics": {
                "forceAtlas2Based": { "gravitationalConstant": -60, "springLength": 100, "springConstant": 0.04, "damping": 0.4 },
                "maxVelocity": 40, "solver": "forceAtlas2Based", "timestep": 0.35
              },
              "interaction": { "hover": true, "navigationButtons": true, "zoomView": true }
            }
            """)

            tmp = os.path.join(tempfile.gettempdir(), "customer_network_hyper.html")
            save_custom_graph(net, tmp, center_person)
            open_url_securely('file://' + tmp)

        except Exception as e:
            err_detail = traceback.format_exc()
            self.load_failed(f"グラフ生成エラー: {str(e)}", err_detail)
        finally:
            self.config(cursor="")

if __name__ == "__main__":
    app = CustomerApp()
    app.mainloop()
