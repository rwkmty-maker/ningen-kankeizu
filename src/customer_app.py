# -*- coding: utf-8 -*-
# VERSION: 108 (バージョンアップ時はこの数値を+1してください)
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import pandas as pd
import threading
import datetime
import traceback
import time
import os
import sys
import logging
import winreg
import re
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from utils import (
    hira_to_kata, normalize_text_unified, get_natural_sort_key, clean_referrer,
    parse_fuzzy_date, parse_excel_date, format_date_text, 
    generate_birth_search_keys, parse_date_with_separators, romaji_to_katakana
)
from graph import generate_customer_graph

# 本番環境用：ログ出力を無効化
# logging.basicConfig(
#     level=logging.DEBUG, 
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('fuzzy_search_debug.log', encoding='utf-8')
#     ]
# )

# バージョン番号（自動取得）
VERSION = 108  # バージョンアップ時はこの数値を+1してください

# レジストリキーパス（アプリ固有）
REGISTRY_KEY = r"Software\CustomerNexusSystem"
REGISTRY_VALUE = "LastOpenedFile"
REGISTRY_GRAPH_DEPTH = "GraphDepth"
REGISTRY_FUZZY_MODE = "FuzzyMode"
REGISTRY_CLAUDE_API_KEY = "ClaudeApiKey"
REGISTRY_CLAUDE_MODEL = "ClaudeModel"

# デフォルトのAPIキーとモデル
DEFAULT_API_KEY = "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"
DEFAULT_MODEL = "claude-opus-4-20250514"


class CustomerApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Customer Nexus System - Hyper Edition Final v{VERSION}")
        self.geometry("1200x800")
        
        # ウィンドウとタスクバーのアイコンを設定
        try:
            if getattr(sys, 'frozen', False):
                # PyInstallerでEXE化された場合
                base_path = sys._MEIPASS
            else:
                # 通常のPythonスクリプト実行時
                base_path = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(base_path, 'app_icon.ico')
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass  # アイコンファイルがない場合はデフォルトのまま
        
        self.df = None
        self.current_indices = None
        self.last_loaded_path = None
        self.last_mod_time = None
        
        self.sort_col = None
        self.sort_asc = True
        self.selected_cols = []
        self.auto_selected_cols = []  # 検索ボタンで自動設定された検索対象を記録
        
        self.click_timer = None 
        self.last_click_time = 0
        self.last_click_col = None
        self.loading = False
        
        # 関係図表示範囲（デフォルト8）
        self.graph_depth = tk.IntVar(value=8)
        
        # 1文字違い表示モード（デフォルト: ON）
        self.fuzzy_mode = tk.StringVar(value="always")  # "always", "off", or "zero_only"
        
        # 検索中止フラグ
        self.search_cancelled = False
        
        # レジストリから設定を復元
        self.load_settings_from_registry() 

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
        self.btn_reload.pack(side=tk.LEFT, padx=5)

        # フリガナ自動入力ボタン（再読込ボタンの右、小さく二段表示）
        self.btn_furigana = tk.Button(frame_top, text="フリガナ\n自動入力",
                                     command=self.auto_fill_furigana,
                                     bg="#9C27B0", fg="white", font=("Meiryo UI", 7, "bold"),
                                     width=6, height=2, relief="flat", cursor="hand2")
        self.btn_furigana.pack(side=tk.LEFT, padx=5)

        self.lbl_status = tk.Label(frame_top, text="ファイルをドロップしてください", 
                                   bg="#111", fg="#00ff41", font=("Meiryo UI", 11))
        self.lbl_status.pack(side=tk.LEFT, padx=10)

        # 表示範囲スイッチ（5ボタン、行間ゼロ）
        frame_depth = tk.Frame(frame_top, bg="#111")
        frame_depth.pack(side=tk.RIGHT, padx=5)
        tk.Label(frame_depth, text="━【関係図の表示範囲】━", 
                 bg="#111", fg="#ffffff", font=("Meiryo UI", 8)).pack(pady=(0, 2))
        frame_depth_buttons = tk.Frame(frame_depth, bg="#111")
        frame_depth_buttons.pack()
        self.depth_buttons = {}
        for depth in [4, 6, 8, 10, 12]:
            btn = tk.Button(frame_depth_buttons, text=str(depth), 
                           command=lambda d=depth: self.set_graph_depth(d),
                           bg="#333", fg="#ffffff", font=("Meiryo UI", 7),
                           width=2, height=1, relief="raised", bd=1)
            btn.pack(side=tk.LEFT, padx=1)
            self.depth_buttons[depth] = btn
        self.update_depth_buttons()
        
        # 1文字違い表示スイッチ（3ボタン、行間ゼロ）
        frame_fuzzy = tk.Frame(frame_top, bg="#111")
        frame_fuzzy.pack(side=tk.RIGHT, padx=5)
        tk.Label(frame_fuzzy, text="━【一文字違い検索】━", 
                 bg="#111", fg="#ffffff", font=("Meiryo UI", 8)).pack(pady=(0, 2))
        frame_fuzzy_buttons = tk.Frame(frame_fuzzy, bg="#111")
        frame_fuzzy_buttons.pack()
        self.fuzzy_buttons = {}
        for mode, text in [("always", "ON"), ("off", "OFF"), ("zero_only", "0件のみ")]:
            btn = tk.Button(frame_fuzzy_buttons, text=text,
                           command=lambda m=mode: self.set_fuzzy_mode(m),
                           bg="#333", fg="#ffffff", font=("Meiryo UI", 7),
                           width=5, height=1, relief="raised", bd=1)
            btn.pack(side=tk.LEFT, padx=1)
            self.fuzzy_buttons[mode] = btn
        self.update_fuzzy_buttons()

        frame_help = tk.Frame(frame_top, bg="#111")
        frame_help.pack(side=tk.RIGHT, padx=5)
        lbl_h1 = tk.Label(frame_help, text="━━━【項目名】━━━\n左クリック：検索対象化\n右クリック：並べ替え　", 
                          bg="#111", fg="#ffffff", font=("Meiryo UI", 8), justify=tk.LEFT)
        lbl_h1.pack(side=tk.LEFT, padx=5)
        lbl_h2 = tk.Label(frame_help, text="━━━【データ】━━━\nダブルクリック：関係図\n右クリック：複数行選択", 
                          bg="#111", fg="#ffffff", font=("Meiryo UI", 8), justify=tk.LEFT)
        lbl_h2.pack(side=tk.LEFT, padx=5)

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
        
        btn_clear = tk.Button(frame_search, text="クリア", command=self.clear_keyword, bg="#666", fg="white")
        btn_clear.pack(side=tk.LEFT, padx=5)
        
        tk.Label(frame_search, text="|", bg="#f0f0f0", fg="#aaa").pack(side=tk.LEFT, padx=5)
        
        # 検索中止ボタン（初期状態は非表示、検索枠の右端に表示、新規検索ボタンと同じサイズ・色）
        self.btn_cancel_search = tk.Button(frame_search, text="⏹ 検索中止", command=self.cancel_search,
                                          bg="#E91E63", fg="white", font=("Meiryo UI", 10, "bold"),
                                          width=10, relief="raised")
        # 初期状態では表示しない（検索中のみ右端に表示）
        
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
        btn_reset.pack(side=tk.LEFT, padx=5)
        
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
        
        self.tree.bind("<Button-1>", self.on_header_click)
        self.tree.bind("<Button-3>", self.on_header_right_click)
        self.tree.bind("<Double-1>", self.on_item_double_click)
        
        self.root = self.winfo_toplevel()
        self.root.bind("<Control-c>", self.copy_selection)
        
        self.check_file_update()
        
        # レジストリから最後に開いたファイルを自動読み込み、またはコマンドライン引数
        self.after(100, self.auto_load_last_file)

    def check_file_update(self):
        """ファイル更新チェック（2秒ごと）"""
        if not self.winfo_exists():
            return
        if self.last_loaded_path:
            try:
                if not os.path.exists(self.last_loaded_path):
                    self.btn_reload.config(bg="#A9A9A9", text="ファイル不明", state=tk.DISABLED)
                else:
                    current_mtime = os.path.getmtime(self.last_loaded_path)
                    if self.last_mod_time and current_mtime > self.last_mod_time:
                        self.btn_reload.config(bg="#FF4500", text="再読込 (更新あり)", fg="white")
                    else:
                        if self.btn_reload.cget('bg') != "#FF4500":
                            self.btn_reload.config(bg="#87CEEB", text="再読込 (更新)", state=tk.NORMAL, fg="black")
            except Exception as e:
                logging.debug(f"ファイル更新チェックエラー: {e}")
        self.after(2000, self.check_file_update)

    def auto_load_last_file(self):
        """起動時の自動読み込み：コマンドライン引数 > レジストリ"""
        try:
            # 1. コマンドライン引数を優先
            if len(sys.argv) > 1:
                file_path = sys.argv[1]
                if os.path.exists(file_path) and file_path.lower().endswith(('.xlsx', '.xlsm', '.xlsb')):
                    self.process_load(file_path)
                    return
            
            # 2. レジストリから最後に開いたファイルを取得
            last_file = self.get_last_opened_file_from_registry()
            if last_file and os.path.exists(last_file):
                self.process_load(last_file)
        except Exception as e:
            logging.debug(f"自動読み込みエラー: {e}")
    
    def get_last_opened_file_from_registry(self):
        """レジストリから最後に開いたファイルパスを取得"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, REGISTRY_VALUE)
            winreg.CloseKey(key)
            return value
        except (OSError, FileNotFoundError):
            return None
    
    def save_last_opened_file_to_registry(self, file_path):
        """レジストリに最後に開いたファイルパスを保存"""
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
            winreg.SetValueEx(key, REGISTRY_VALUE, 0, winreg.REG_SZ, file_path)
            winreg.CloseKey(key)
        except Exception as e:
            logging.debug(f"レジストリ保存エラー: {e}")
    
    def update_title_with_path(self, file_path):
        """タイトルバーにファイルパスを表示"""
        try:
            self.title(f"Customer Nexus System - Hyper Edition Final v{VERSION} ［{file_path}］")
        except Exception as e:
            logging.debug(f"タイトル更新エラー: {e}")
    
    def load_settings_from_registry(self):
        """レジストリから設定を復元"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_READ)
            
            # 表示範囲を復元
            try:
                depth, _ = winreg.QueryValueEx(key, REGISTRY_GRAPH_DEPTH)
                self.graph_depth.set(int(depth))
            except:
                pass
            
            # 1文字違いモードを復元
            try:
                mode, _ = winreg.QueryValueEx(key, REGISTRY_FUZZY_MODE)
                self.fuzzy_mode.set(mode)
            except:
                pass
            
            winreg.CloseKey(key)
        except:
            pass
    
    def save_settings_to_registry(self):
        """レジストリに設定を保存"""
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
            winreg.SetValueEx(key, REGISTRY_GRAPH_DEPTH, 0, winreg.REG_DWORD, self.graph_depth.get())
            winreg.SetValueEx(key, REGISTRY_FUZZY_MODE, 0, winreg.REG_SZ, self.fuzzy_mode.get())
            winreg.CloseKey(key)
        except Exception as e:
            logging.debug(f"設定保存エラー: {e}")
    
    def set_graph_depth(self, depth):
        """表示範囲を設定"""
        self.graph_depth.set(depth)
        self.update_depth_buttons()
        self.save_settings_to_registry()
    
    def set_fuzzy_mode(self, mode):
        """1文字違いモードを設定"""
        self.fuzzy_mode.set(mode)
        self.update_fuzzy_buttons()
        self.save_settings_to_registry()
        # 検索結果を再表示
        if self.df is not None and self.current_indices is not None:
            self.update_list()
    
    def update_depth_buttons(self):
        """表示範囲ボタンの色を更新"""
        current = self.graph_depth.get()
        for depth, btn in self.depth_buttons.items():
            if depth == current:
                btn.config(bg="#FF8C00", relief="sunken")  # 暗いオレンジ色
            else:
                btn.config(bg="#333", relief="raised")
    
    def update_fuzzy_buttons(self):
        """1文字違いボタンの色を更新"""
        current = self.fuzzy_mode.get()
        for mode, btn in self.fuzzy_buttons.items():
            if mode == current:
                btn.config(bg="#FF8C00", relief="sunken")  # 暗いオレンジ色
            else:
                btn.config(bg="#333", relief="raised")
    
    def levenshtein_distance(self, s1, s2):
        """レーベンシュタイン距離（編集距離）を計算"""
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def check_fuzzy_match(self, query, target):
        """シンプルな編集距離チェック（編集距離1のみ許可）"""
        query_len = len(query)
        
        # 1文字の場合は曖昧検索しない
        if query_len <= 1:
            return False
        
        # 編集距離が1かチェック
        dist = self.levenshtein_distance(query, target)
        return dist == 1
    
    def check_fuzzy_match_with_substring(self, query, target, col_name):
        """部分文字列を含む編集距離チェック（電話番号・住所列用）"""
        query_len = len(query)
        
        # 1文字の場合は曖昧検索しない
        if query_len <= 1:
            return False
        
        # 5文字以上の場合は部分文字列チェックをスキップ（負荷軽減）
        if query_len >= 5:
            return self.check_fuzzy_match(query, target)
        
        # 電話番号列または住所列の場合は部分文字列チェック
        is_phone_or_address = '電話番号' in col_name or '住所' in col_name
        
        if is_phone_or_address and len(target) >= query_len:
            # targetから query_len と同じ長さの部分文字列を抽出
            for i in range(len(target) - query_len + 1):
                substring = target[i:i + query_len]
                if self.check_fuzzy_match(query, substring):
                    return True
            # 1文字長い部分文字列もチェック（追加の場合）
            for i in range(len(target) - query_len):
                substring = target[i:i + query_len + 1]
                if self.check_fuzzy_match(query, substring):
                    return True
            return False
        
        # 名前列などは部分文字列もチェック
        if len(target) >= query_len:
            # 同じ長さの部分文字列をチェック
            for i in range(len(target) - query_len + 1):
                substring = target[i:i + query_len]
                if self.check_fuzzy_match(query, substring):
                    return True
            # 1文字長い部分文字列もチェック（追加の場合）
            for i in range(len(target) - query_len):
                substring = target[i:i + query_len + 1]
                if self.check_fuzzy_match(query, substring):
                    return True
        
        return self.check_fuzzy_match(query, target)
    
    def get_fuzzy_matches(self):
        """1文字違いの曖昧マッチを取得（1文字検索は除外、部分文字列対応）"""
        try:
            query = self.entry_search.get().strip()
            
            # 1文字の場合は曖昧検索しない
            if len(query) <= 1:
                return []
            
            # キーワードが空の場合は曖昧検索しない
            if not query:
                return []
            
            # 検索中止ボタンを表示
            self.btn_cancel_search.pack(side=tk.RIGHT, padx=10)
            self.update_idletasks()
            
            # 正規化
            q_norm = normalize_text_unified(query)
            q_kana = normalize_text_unified(hira_to_kata(query))
            
            # 検索対象列を決定（第一段階と同じ列を使用）
            if self.selected_cols:
                search_cols = [c for c in self.selected_cols if c in self.df.columns]
            else:
                # search_indexがある場合はそれを使用（全列結合済み）
                if 'search_index' in self.df.columns:
                    search_cols = ['search_index']
                else:
                    # search_indexがない場合は全列を検索対象にする
                    exclude_cols = ['__sort_birth__', '__birth_year__', '__birth_month__', '__birth_day__', 
                                   '__bg_color__', '__sk_', 'search_index']
                    search_cols = [c for c in self.df.columns if not any(ex in c for ex in exclude_cols)]
            
            fuzzy_matches = []
            already_matched = set(self.current_indices)  # 既にマッチしているものは除外
            
            # 全データに対して編集距離をチェック
            check_count = 0
            for idx in self.df.index:
                # 中断チェック（100件ごと）
                check_count += 1
                if check_count % 100 == 0:
                    if self.search_cancelled:
                        logging.info("一文字違い検索が中断されました")
                        break
                    self.update_idletasks()  # UIを更新
                
                if idx in already_matched:
                    continue
                
                row = self.df.loc[idx]
                
                # 各検索対象列をチェック
                for col in search_cols:
                    if col not in row:
                        continue
                    
                    cell_value = str(row[col])
                    if not cell_value or cell_value == '':
                        continue
                    
                    # 正規化して比較
                    cell_norm = normalize_text_unified(cell_value)
                    
                    # 部分文字列を含む編集距離チェック
                    if self.check_fuzzy_match_with_substring(q_norm, cell_norm, col):
                        fuzzy_matches.append(idx)
                        break
                    
                    # カナ変換でもチェック
                    if self.check_fuzzy_match_with_substring(q_kana, cell_norm, col):
                        fuzzy_matches.append(idx)
                        break
            
            # 検索中止ボタンを非表示
            self.btn_cancel_search.pack_forget()
            
            return fuzzy_matches  # 上限なし（検索中止ボタンで停止可能）
        except Exception as e:
            logging.error(f"曖昧検索エラー: {e}")
            # 検索中止ボタンを非表示
            self.btn_cancel_search.pack_forget()
            return []
    
    def get_fuzzy_matches_for_keywords(self, keyword_groups):
        """AND/OR検索用の一文字違い検索
        
        正しいアルゴリズム:
        第二段階では「通常部分一致 OR 一文字違い」のAND検索を行う
        
        例: 「出禁 070」の場合
        A = 「出禁を含む」OR「出禁の一文字違い」
        B = 「070を含む」OR「070の一文字違い」
        result = A ∩ B - 第一段階の結果
        """
        try:
            if not keyword_groups:
                return []
            
            # 検索中止ボタンを表示
            self.btn_cancel_search.pack(side=tk.RIGHT, padx=10)
            self.update_idletasks()
            
            # 検索対象列を決定（第一段階と同じ列を使用）
            if self.selected_cols:
                search_cols = [c for c in self.selected_cols if c in self.df.columns]
            else:
                # search_indexがある場合はそれを使用（全列結合済み）
                if 'search_index' in self.df.columns:
                    search_cols = ['search_index']
                else:
                    # search_indexがない場合は全列を検索対象にする
                    exclude_cols = ['__sort_birth__', '__birth_year__', '__birth_month__', '__birth_day__', 
                                   '__bg_color__', '__sk_', 'search_index']
                    search_cols = [c for c in self.df.columns if not any(ex in c for ex in exclude_cols)]
            
            first_stage_matched = set(self.current_indices)  # 第一段階でマッチした行（最後に除外）
            or_results = []  # ORグループの結果を格納
            
            # ORグループごとに処理
            for and_group in keyword_groups:
                # ANDグループ内の各キーワードで「通常部分一致 OR 一文字違い」マッチを取得
                and_results = []
                
                for keyword in and_group:
                    if len(keyword) <= 1:
                        continue
                    
                    q_norm = normalize_text_unified(keyword)
                    q_kana = normalize_text_unified(hira_to_kata(keyword))
                    
                    keyword_matches = set()
                    
                    # 全行をチェック（第一段階の結果も含む）
                    for idx in self.df.index:
                        if self.search_cancelled:
                            break
                        
                        row = self.df.loc[idx]
                        
                        # 各列をチェック
                        for col in search_cols:
                            if col not in row:
                                continue
                            
                            cell_value = str(row[col])
                            if not cell_value or cell_value == '':
                                continue
                            
                            cell_norm = normalize_text_unified(cell_value)
                            
                            # 通常部分一致チェック
                            if q_norm in cell_norm:
                                keyword_matches.add(idx)
                                break
                            
                            # 一文字違いチェック
                            if self.check_fuzzy_match_with_substring(q_norm, cell_norm, col):
                                keyword_matches.add(idx)
                                break
                            
                            # カナでもチェック
                            if q_kana != q_norm:
                                if q_kana in cell_norm:
                                    keyword_matches.add(idx)
                                    break
                                if self.check_fuzzy_match_with_substring(q_kana, cell_norm, col):
                                    keyword_matches.add(idx)
                                    break
                    
                    and_results.append(keyword_matches)
                
                # ANDグループの積集合を計算
                if and_results:
                    group_result = and_results[0]
                    for i in range(1, len(and_results)):
                        group_result = group_result & and_results[i]
                    
                    if group_result:
                        or_results.extend(list(group_result))
            
            # 検索中止ボタンを非表示
            self.btn_cancel_search.pack_forget()
            
            # 第一段階の結果を除外して返す
            final_result = [idx for idx in set(or_results) if idx not in first_stage_matched]
            return final_result  # 上限なし（検索中止ボタンで停止可能）
        except Exception as e:
            traceback.print_exc()
            self.btn_cancel_search.pack_forget()
            return []

    def on_drop(self, event):
        """ドラッグ&ドロップ処理"""
        try:
            path = event.data.replace('{', '').replace('}', '')
            if path.lower().endswith(('.xlsx', '.xlsm', '.xlsb')):
                self.process_load(path)
        except Exception as e:
            messagebox.showerror("Error", f"ドロップ処理エラー: {e}")

    def start_load_excel(self):
        """ファイル選択ダイアログ"""
        try:
            path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xlsm *.xlsb")])
            if path:
                self.process_load(path)
        except Exception as e:
            messagebox.showerror("Error", f"ファイル選択エラー: {e}")

    def reload_excel(self):
        """再読み込み"""
        try:
            if self.last_loaded_path and os.path.exists(self.last_loaded_path):
                self.process_load(self.last_loaded_path)
            else:
                messagebox.showerror("エラー", "再読み込みするファイルが見つかりません。")
        except Exception as e:
            messagebox.showerror("Error", f"再読み込みエラー: {e}")

    def process_load(self, file_path):
        """読み込み開始"""
        if hasattr(self, 'loading') and self.loading:
            return
        
        try:
            self.loading = True
            self.btn_load.config(state=tk.DISABLED)
            if self.btn_reload.winfo_ismapped():
                self.btn_reload.config(state=tk.DISABLED)
                
            self.lbl_status.config(text="データ読み込み中...", fg="#00ff41")
            self.progress.pack(side=tk.LEFT, padx=10)
            self.progress.start(5)  # 速度を上げて動いていることを明確に
            self.update_idletasks()  # UIを即座に更新
            threading.Thread(target=self.load_thread, args=(file_path,), daemon=True).start()
        except Exception as e:
            self.loading = False
            messagebox.showerror("Error", f"読み込み開始エラー: {e}")

    def load_thread(self, path):
        """バックグラウンド読み込み処理"""
        try:
            if not os.path.exists(path):
                raise FileNotFoundError(f"ファイルが見つかりません: {path}")

            try:
                # 進捗表示用のコールバック
                def update_load_status(current, total):
                    self.after(0, lambda: self.lbl_status.config(
                        text=f"データ読み込み中... {current}/{total}行", fg="#00ff41"))
                
                # 数値データを保持したまま読み込み（dtype指定なし）
                self.after(0, lambda: self.lbl_status.config(text="Excelファイルを読み込み中...", fg="#00ff41"))
                df = pd.read_excel(path)
                
                # openpyxlで会員IDと背景色情報を読み取り（空行削除前）
                bg_color_dict = {}  # 行番号をキーとした辞書
                member_id_dict = {}  # 会員IDを格納する辞書
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(path, data_only=True)  # data_only=Trueで数式の計算結果を取得
                    ws = wb.active
                    
                    # 会員ID列のインデックスを取得
                    member_id_col = None
                    for col_idx, cell in enumerate(ws[1], start=1):
                        if cell.value == '会員ID':
                            member_id_col = col_idx
                            break
                    
                    # ヘッダー行をスキップして2行目から読み取り
                    total_rows = ws.max_row - 1
                    for row_idx in range(2, ws.max_row + 1):
                        # 進捗表示（50行ごと）
                        if (row_idx - 2) % 50 == 0:
                            update_load_status(row_idx - 1, total_rows)
                        
                        # 会員IDを読み取り（数式の計算結果）
                        if member_id_col:
                            member_id_cell = ws.cell(row=row_idx, column=member_id_col)
                            if member_id_cell.value is not None:
                                member_id_dict[row_idx - 2] = str(member_id_cell.value)
                        
                        # 最初のセルの背景色を取得（代表として）
                        cell = ws.cell(row=row_idx, column=1)
                        fill = cell.fill
                        
                        # 背景色が設定されているか確認（fgColorとbgColorの両方をチェック）
                        hex_color = None
                        if fill:
                            try:
                                # fgColorをチェック
                                if hasattr(fill, 'fgColor') and fill.fgColor:
                                    color = fill.fgColor
                                    
                                    # RGB値が直接設定されている場合
                                    if color.rgb and color.rgb is not None:
                                        rgb_str = color.rgb
                                        if isinstance(rgb_str, str) and len(rgb_str) >= 6:
                                            # ARGB形式の場合、最初の2文字（アルファ値）を除去
                                            if len(rgb_str) == 8:
                                                hex_color = f'#{rgb_str[2:]}'
                                            else:
                                                hex_color = f'#{rgb_str}'
                                    
                                    # indexedカラーの場合（簡易的なマッピング）
                                    elif color.indexed is not None:
                                        indexed_colors = {
                                            2: '#FF0000',   # 赤
                                            3: '#00FF00',   # 緑
                                            4: '#0000FF',   # 青
                                            5: '#FFFF00',   # 黄
                                            6: '#FF00FF',   # マゼンタ
                                            7: '#00FFFF',   # シアン
                                            10: '#FF0000',  # 赤
                                            45: '#FFA500',  # オレンジ
                                            50: '#FFA500',  # オレンジ
                                        }
                                        if color.indexed in indexed_colors:
                                            hex_color = indexed_colors[color.indexed]
                                
                                # bgColorもチェック（fgColorで取得できなかった場合）
                                if not hex_color and hasattr(fill, 'bgColor') and fill.bgColor:
                                    color = fill.bgColor
                                    
                                    if color.rgb and color.rgb is not None:
                                        rgb_str = color.rgb
                                        if isinstance(rgb_str, str) and len(rgb_str) >= 6:
                                            if len(rgb_str) == 8:
                                                hex_color = f'#{rgb_str[2:]}'
                                            else:
                                                hex_color = f'#{rgb_str}'
                                    
                                    elif color.indexed is not None:
                                        indexed_colors = {
                                            2: '#FF0000', 3: '#00FF00', 4: '#0000FF', 5: '#FFFF00',
                                            6: '#FF00FF', 7: '#00FFFF', 10: '#FF0000',
                                            45: '#FFA500', 50: '#FFA500',
                                        }
                                        if color.indexed in indexed_colors:
                                            hex_color = indexed_colors[color.indexed]
                                
                                # 白や極端に薄い色、黒は無視
                                if hex_color and hex_color.upper() not in ['#FFFFFF', '#FFFFFFFF', '#000000', '#FEFEFE', '#00000000']:
                                    bg_color_dict[row_idx - 2] = hex_color
                            except Exception as e:
                                # 個別セルのエラーは無視して続行
                                pass
                    
                    wb.close()
                except Exception as e:
                    # 背景色読み取りに失敗しても処理は続行
                    logging.debug(f"背景色・会員ID読み取りエラー: {e}")
                    member_id_dict = {}
                    
            except PermissionError:
                raise PermissionError("ファイルが開かれているか、アクセス権限がありません。\nExcelを閉じてから再試行してください。")
            except Exception as e:
                raise Exception(f"Excel読み込みエラー: {e}")

            # NaNを空文字列に変換
            df = df.fillna('')
            
            # openpyxlで読み取った会員IDをDataFrameに反映
            if member_id_dict and '会員ID' in df.columns:
                for idx, member_id in member_id_dict.items():
                    if idx < len(df):
                        df.at[idx, '会員ID'] = member_id
            
            required = ['登録名']
            for col in required:
                if col not in df.columns:
                    raise Exception(f"必須列「{col}」不足")

            # 登録名・本名・フリガナ・生年月日・住所・電話番号・電話番号2・電話番号3のいずれも空の行を除外（ベクトル化）
            check_cols = ['登録名', '本名', 'フリガナ', '生年月日', '住所', '電話番号', '電話番号2', '電話番号3']
            existing_check_cols = [col for col in check_cols if col in df.columns]
            if existing_check_cols:
                # ベクトル化: 各列が空文字列かどうかをチェック（高速化）
                empty_mask = (df[existing_check_cols] == '').all(axis=1)
                # 空行削除前のインデックスを保存
                original_indices = df.index[~empty_mask].tolist()
                df = df[~empty_mask].reset_index(drop=True)
                
                # 背景色情報を新しいDataFrameにマッピング
                bg_colors = [bg_color_dict.get(orig_idx, '') for orig_idx in original_indices]
                df['__bg_color__'] = bg_colors
                
                # 全セルを対象に色分け（背景色がない場合のみ適用）
                # 優先順位：自主出禁 > 出禁 > 新規・紹介NG > サビ禁
                exclude_color_cols = ['__sort_birth__', '__birth_year__', '__birth_month__', '__birth_day__', 
                                      '__bg_color__', '__sk_', 'search_index']
                color_check_cols = [c for c in df.columns if not any(ex in c for ex in exclude_color_cols)]
                
                for idx in range(len(df)):
                    if df.at[idx, '__bg_color__']:  # 既に背景色がある場合はスキップ
                        continue
                    
                    # 全セルを結合してチェック
                    all_text = ''
                    for col in color_check_cols:
                        cell_val = str(df.at[idx, col]).strip()
                        if cell_val and cell_val != 'nan':
                            all_text += ' ' + cell_val
                    
                    # 優先順位1: 自主出禁（オレンジ）
                    if '自主出禁' in all_text:
                        df.at[idx, '__bg_color__'] = '#FFC000'
                        continue
                    
                    # 優先順位2: 出禁（赤）
                    if '出禁' in all_text:
                        df.at[idx, '__bg_color__'] = '#FF3300'
                        continue
                    
                    # 優先順位3: 新規・紹介NG（紫）
                    has_shinki_shoukai = ('新規' in all_text or '紹介' in all_text)
                    ng_words = ['不可', 'だめ', 'ダメ', '駄目', '拒否', 'NG', 'ＮＧ', '受けない', '受けるな', '×']
                    has_ng = any(ng in all_text for ng in ng_words)
                    if has_shinki_shoukai and has_ng:
                        df.at[idx, '__bg_color__'] = '#9C27B0'
                        continue
                    
                    # 優先順位4: サービス禁止系（緑）
                    # {サビ,サービス}と{禁,停,無,止,ＮＧ,NG,なし,×}が隣接
                    sabi_pattern = r'(サビ|サービス)(禁|停|無|止|ＮＧ|NG|なし|×)'
                    if re.search(sabi_pattern, all_text):
                        df.at[idx, '__bg_color__'] = '#00FF00'
            
            birth_col_dates = None
            if '生年月日' in df.columns:
                birth_col_dates = df['生年月日'].apply(parse_excel_date)
                
                def format_date_row(val, dt):
                    if pd.notna(dt):
                        return format_date_text(dt)
                    return str(val) if val != '' else ''
                
                df['生年月日'] = [format_date_row(v, d) for v, d in zip(df['生年月日'], birth_col_dates)]

            # 生年月日と背景色列以外の列を文字列として確実に変換
            for col in df.columns:
                if col not in ['生年月日', '__bg_color__']:
                    df[col] = df[col].astype(str)
                    # 'nan'という文字列になっている場合は空文字列に変換
                    df[col] = df[col].replace('nan', '')
            
            if birth_col_dates is not None:
                df['__sort_birth__'] = birth_col_dates
                df['__birth_year__'] = birth_col_dates.apply(lambda x: x.year if pd.notna(x) else None)
                df['__birth_month__'] = birth_col_dates.apply(lambda x: x.month if pd.notna(x) else None)
                df['__birth_day__'] = birth_col_dates.apply(lambda x: x.day if pd.notna(x) else None)

            for col in df.columns:
                if col.startswith('__'):
                    continue
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
        """読み込み成功時の処理"""
        try:
            self.df = df
            self.current_indices = df.index
            self.last_loaded_path = path
            try:
                self.last_mod_time = os.path.getmtime(path)
            except:
                self.last_mod_time = time.time()
            
            # レジストリに保存
            self.save_last_opened_file_to_registry(path)
            
            # タイトルバーを更新
            self.update_title_with_path(path)
            
            self.loading = False
            self.progress.stop()
            self.progress.pack_forget()
            self.btn_load.config(state=tk.NORMAL)
            
            self.btn_reload.pack(side=tk.LEFT, padx=10)
            self.btn_reload.config(bg="#87CEEB", text="再読込 (更新)", state=tk.NORMAL, fg="black")
            
            self.lbl_status.config(text=f"✅ 読込完了: {len(df)}件\n{os.path.basename(path)}", fg="#00ff41")
            
            self.sort_col = None
            self.sort_asc = True
            
            disp_cols = [c for c in df.columns if not c.startswith('__') and c != 'search_index']
            self.tree['columns'] = disp_cols
            for c in disp_cols:
                self.tree.heading(c, text=c)
                width = 100
                
                # 列幅調整（指定された割合で調整）
                if c == '会員ID':
                    width = 20  # 33 * 0.60
                elif c == '登録名':
                    width = 72
                elif c == 'フリガナ':
                    width = 99  # 110 * 0.90
                elif c == '旧登録名':
                    width = 50
                elif c == '本名':
                    width = 70  # 50 * 1.40
                elif c == '日付登録':
                    width = 80
                elif c == '生年月日':
                    width = 137  # 125 + 12 (半角2文字分広く)
                elif c == '住所':
                    width = 378  # 390 - 12 (半角2文字分狭く)
                elif c == '職業/勤務先':
                    width = 80
                elif c == '電話番号':
                    width = 118  # 107 * 1.10
                elif c == '電話番号2':
                    width = 118  # 107 * 1.10
                elif c == '電話番号3':
                    width = 118  # 107 * 1.10
                elif c == '担当者':
                    width = 60
                elif c == '紹介者':
                    width = 60
                elif c == 'グループ':
                    width = 30
                elif c == '出禁種別':
                    width = 18
                elif c == 'メール':
                    width = 30
                elif c == 'LINE':
                    width = 30
                elif c == 'メモ1':
                    width = 30
                elif c == 'メモ2':
                    width = 30
                elif c == '身分証1':
                    width = 6  # 15 * 0.40
                elif c == '身分証2':
                    width = 6  # 15 * 0.40
                elif c == '身分証チェック':
                    width = 6  # 15 * 0.40
                elif c == '記入者':
                    width = 6  # 15 * 0.40
                elif c == 'アナウンス可能(時間帯)':
                    width = 7  # 18 * 0.40
                elif c == 'チケット欄':
                    width = 6  # 15 * 0.40
                elif c == '備考':
                    width = 450  # 600 * 0.75
                
                self.tree.column(c, width=width)
                
            self.update_list()
        except Exception as e:
            messagebox.showerror("Error", f"読み込み成功処理エラー: {e}")

    def load_failed(self, msg, detail):
        """読み込み失敗時の処理"""
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

    def on_header_click(self, event):
        """ヘッダー左クリック：検索対象列の選択/解除"""
        try:
            region = self.tree.identify("region", event.x, event.y)
            if region == "heading":
                col_id = self.tree.identify_column(event.x)
                col_name = self.tree.column(col_id, "id")
                if col_name in self.selected_cols:
                    self.selected_cols.remove(col_name)
                    # auto_selected_colsからも削除
                    if col_name in self.auto_selected_cols:
                        self.auto_selected_cols.remove(col_name)
                else:
                    self.selected_cols.append(col_name)
                    # 手動設定なのでauto_selected_colsには追加しない
                self.update_heading_display()
                self.run_search_new(apply_sort=False)
        except Exception as e:
            logging.debug(f"ヘッダークリックエラー: {e}")

    def on_header_right_click(self, event):
        """ヘッダー右クリック：ソート、データ右クリック：複数選択"""
        try:
            region = self.tree.identify("region", event.x, event.y)
            if region == "heading":
                col_id = self.tree.identify_column(event.x)
                col_name = self.tree.column(col_id, "id")
                if self.sort_col == col_name:
                    if self.sort_asc is True:
                        self.sort_asc = False
                    elif self.sort_asc is False:
                        self.sort_col = None
                        self.sort_asc = True
                    else:
                        self.sort_asc = True 
                else:
                    self.sort_col = col_name
                    self.sort_asc = True
                self.run_single_sort()
            elif region == "cell":
                row_id = self.tree.identify_row(event.y)
                if row_id:
                    sel = list(self.tree.selection())
                    if row_id not in sel:
                        sel.append(row_id)
                        self.tree.selection_set(sel)
        except Exception as e:
            pass

    def update_heading_display(self):
        """ヘッダー表示更新"""
        try:
            for col in self.tree["columns"]:
                text = col
                if self.sort_col == col:
                    text += " ▲" if self.sort_asc else " ▼"
                if col in self.selected_cols:
                    text = f"☑ {text}"
                self.tree.heading(col, text=text)
            if self.selected_cols:
                text = "検索対象: " + " , ".join(self.selected_cols)
                self.lbl_selected_cols.config(text=text, bg="#FFE4B5")
            else:
                self.lbl_selected_cols.config(text="検索対象: 全列", bg="#f0f0f0")
        except Exception as e:
            pass

    def set_cols_and_search(self, cols, sort_by_birth=False):
        """検索対象列を設定して検索実行"""
        try:
            self.selected_cols = cols
            self.auto_selected_cols = cols.copy()  # 自動設定された検索対象を記録
            self.update_heading_display()
            if sort_by_birth:
                self.sort_col = '生年月日'
                self.sort_asc = True
                self.run_search_new(apply_sort=True)
            else:
                self.run_search_new(apply_sort=False)
        except Exception as e:
            messagebox.showerror("Error", f"検索設定エラー: {e}")

    def parse_search_keywords(self, query):
        """キーワードをAND/ORに解析
        
        AND区切り: 1つまたは複数のスペース（全角・半角）
        OR区切り: 0個以上のスペースに囲まれた1つ以上の「｜」または「|」
        
        ローマ字入力対策: ローマ字を含むキーワードはカタカナ変換結果もOR検索
        例: 'yappu-' → 元のキーワードとカタカナ変換('ヤップー')の両方で検索
        """
        try:
            # OR区切り文字で分割（スペースに囲まれた｜または|の連続）
            or_pattern = r'[\s　]*[｜|]+[\s　]*'
            or_groups = re.split(or_pattern, query)
            
            result = []
            for group in or_groups:
                # AND区切り文字で分割（1つ以上のスペース、全角・半角）
                and_pattern = r'[\s　]+'
                and_keywords = [k.strip() for k in re.split(and_pattern, group) if k.strip()]
                if and_keywords:
                    result.append(and_keywords)
            
            # ローマ字入力対策: 各キーワードにローマ字が含まれていたらカタカナ変換結果もOR追加
            expanded_result = []
            for and_group in result:
                # このANDグループとローマ字変換版のANDグループを作成
                has_romaji = False
                converted_group = []
                for keyword in and_group:
                    # ローマ字（a-z）を含むかチェック
                    if re.search(r'[a-zA-Z]', keyword):
                        has_romaji = True
                        converted = romaji_to_katakana(keyword)
                        converted_group.append(converted)
                    else:
                        converted_group.append(keyword)
                
                # 元のANDグループを追加
                expanded_result.append(and_group)
                
                # ローマ字が含まれていて、変換後が元と異なる場合はOR条件として追加
                if has_romaji and converted_group != and_group:
                    expanded_result.append(converted_group)
            
            return expanded_result  # [["田中", "太郎"], ["山田", "花子"]]
        except Exception as e:
            logging.error(f"キーワード解析エラー: {e}")
            return [[query.strip()]]
    
    def get_search_mask(self, source_indices):
        """検索マスク生成（AND/OR検索対応、生年月日は年月日を分離して検索）"""
        if self.df is None:
            return None
        
        try:
            query = self.entry_search.get()
            
            # キーワードが空の場合は全件返す
            if not query.strip():
                return pd.Series([True] * len(source_indices), index=source_indices)
            
            # AND/OR解析
            keyword_groups = self.parse_search_keywords(query)
            
            # 単一キーワードの場合は従来の検索ロジック
            if len(keyword_groups) == 1 and len(keyword_groups[0]) == 1:
                return self.get_single_keyword_mask(keyword_groups[0][0], source_indices)
            
            # 複数キーワード：AND/OR検索
            subset = self.df.loc[source_indices]
            or_mask = pd.Series([False] * len(subset), index=subset.index)
            
            for and_group in keyword_groups:
                and_mask = pd.Series([True] * len(subset), index=subset.index)
                for keyword in and_group:
                    single_mask = self.get_single_keyword_mask(keyword, subset.index)
                    and_mask = and_mask & single_mask
                or_mask = or_mask | and_mask
            
            return or_mask
        except Exception as e:
            messagebox.showerror("Error", f"検索マスク生成エラー: {e}")
            return pd.Series([True] * len(source_indices), index=source_indices)
    
    def get_single_keyword_mask(self, query, source_indices):
        """単一キーワードの検索マスク生成（従来のロジック）"""
        if self.df is None:
            return None
        
        try:
            # キーワードが空の場合は全件返す
            if not query.strip():
                return pd.Series([True] * len(source_indices), index=source_indices)

            q_norm_base = normalize_text_unified(query)
            q_kana_conv = normalize_text_unified(hira_to_kata(query))

            subset = self.df.loc[source_indices]
            mask = pd.Series([False] * len(subset), index=subset.index)

            # 通常のテキスト検索
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

            # 生年月日検索（改善版：年月日を分離して検索）
            do_date_search = True
            if self.selected_cols and '生年月日' not in self.selected_cols:
                do_date_search = False
            
            if do_date_search and query.strip() and all(col in self.df.columns for col in ['__birth_year__', '__birth_month__', '__birth_day__']):
                # 区切り文字がある場合は直接パース
                parsed_date = parse_date_with_separators(query)
                if parsed_date:
                    y, m, d = parsed_date
                    date_mask = pd.Series([True] * len(subset), index=subset.index)
                    if y is not None:
                        date_mask = date_mask & (subset['__birth_year__'] == y)
                    if m is not None:
                        date_mask = date_mask & (subset['__birth_month__'] == m)
                    if d is not None:
                        date_mask = date_mask & (subset['__birth_day__'] == d)
                    mask = mask | date_mask
                else:
                    # 区切り文字がない場合は全パターンで検索
                    target_dates = parse_fuzzy_date(query)
                    if target_dates:
                        for (y, m, d) in target_dates:
                            date_mask = pd.Series([True] * len(subset), index=subset.index)
                            if y is not None:
                                date_mask = date_mask & (subset['__birth_year__'] == y)
                            if m is not None:
                                date_mask = date_mask & (subset['__birth_month__'] == m)
                            if d is not None:
                                date_mask = date_mask & (subset['__birth_day__'] == d)
                            mask = mask | date_mask
            
            return mask
        except Exception as e:
            messagebox.showerror("Error", f"検索マスク生成エラー: {e}")
            return pd.Series([True] * len(source_indices), index=source_indices)

    def run_search_new(self, apply_sort=False):
        """新規検索（第一段階：部分一致AND検索、第二段階：一文字違いAND検索）"""
        try:
            if self.df is None:
                return
            
            # オペレーターが手動で設定した検索対象がない場合のみ、自動設定をクリア
            manual_cols = [col for col in self.selected_cols if col not in self.auto_selected_cols]
            if not manual_cols:
                self.auto_selected_cols = []  # 自動設定をクリア
            
            # 第一段階：部分一致AND検索
            query = self.entry_search.get().strip()
            mask = self.get_search_mask(self.df.index)
            self.current_indices = self.df.index[mask]
            
            # 第二段階：一文字違いAND検索（曖昧検索モードがONの場合のみ）
            fuzzy_mode = self.fuzzy_mode.get()
            should_fuzzy = (fuzzy_mode == "always") or (fuzzy_mode == "zero_only" and len(self.current_indices) == 0)
            
            if should_fuzzy and query:
                keyword_groups = self.parse_search_keywords(query)
                
                # AND/OR検索の場合は各キーワードを一文字違い検索
                if keyword_groups and (len(keyword_groups) > 1 or len(keyword_groups[0]) > 1):
                    fuzzy_indices = self.get_fuzzy_matches_for_keywords(keyword_groups)
                else:
                    # 単一キーワードの場合は従来の一文字違い検索
                    fuzzy_indices = self.get_fuzzy_matches()
                
                if fuzzy_indices and not self.search_cancelled:
                    # 重複を除外してcurrent_indicesに追加
                    fuzzy_only = [idx for idx in fuzzy_indices if idx not in self.current_indices]
                    if fuzzy_only:
                        self.current_indices = self.current_indices.append(pd.Index(fuzzy_only))
            
            if apply_sort and '__sort_birth__' in self.df.columns:
                self.sort_col = '生年月日'
                self.sort_asc = True
                self.run_single_sort()
            else:
                if self.sort_col:
                    self.run_single_sort()
                else:
                    self.update_list()
            self.update_status_msg("新規検索結果")
        except Exception as e:
            messagebox.showerror("Error", f"新規検索エラー: {e}")

    def run_search_filter(self):
        """絞り込み検索"""
        try:
            if self.df is None:
                return
            mask = self.get_search_mask(self.current_indices)
            self.current_indices = self.current_indices[mask]
            if self.sort_col:
                self.run_single_sort()
            else:
                self.update_list()
            self.update_status_msg("絞り込み結果")
        except Exception as e:
            messagebox.showerror("Error", f"絞り込み検索エラー: {e}")

    def run_single_sort(self):
        """ソート実行"""
        try:
            if self.df is None or len(self.current_indices) == 0:
                self.update_list()
                self.update_heading_display()
                return
            
            if not self.sort_col:
                self.current_indices = self.current_indices.sort_values()
                self.update_heading_display()
                self.update_list()
                self.lbl_status.config(text="ソート解除", fg="#00ffff")
                return

            subset = self.df.loc[self.current_indices]
            target = self.sort_col
            if self.sort_col == '生年月日' and '__sort_birth__' in self.df.columns:
                target = '__sort_birth__'
            elif f'__sk_{self.sort_col}' in self.df.columns:
                target = f'__sk_{self.sort_col}'
            
            sorted_indices = subset.sort_values(by=target, ascending=self.sort_asc, na_position='last').index
            self.current_indices = sorted_indices
            self.update_heading_display()
            self.update_list()
            state_text = '昇順' if self.sort_asc else '降順'
            self.lbl_status.config(text=f"ソート: {self.sort_col} [{state_text}]", fg="#00ffff")
        except Exception as e:
            traceback.print_exc()
            self.lbl_status.config(text="ソートエラー", fg="red")

    def update_status_msg(self, prefix):
        """ステータスメッセージ更新"""
        try:
            msg = f"{prefix}: {len(self.current_indices)}件"
            if self.selected_cols:
                msg += f" (対象: {','.join(self.selected_cols)})"
            self.lbl_status.config(text=msg, fg="orange")
        except Exception as e:
            pass

    def copy_selection(self, event):
        """Ctrl+Cでコピー"""
        try:
            selected_items = self.tree.selection()
            if not selected_items:
                return
            copy_text = ""
            for item in selected_items:
                vals = self.tree.item(item, "values")
                copy_text += "\t".join([str(v) for v in vals]) + "\n"
            self.root.clipboard_clear()
            self.root.clipboard_append(copy_text)
            self.lbl_status.config(text=f"コピー: {len(selected_items)}行", fg="green")
        except Exception as e:
            pass

    def clear_keyword(self):
        """キーワード入力欄をクリア"""
        try:
            self.entry_search.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"クリアエラー: {e}")

    def cancel_search(self):
        """検索を中止"""
        self.search_cancelled = True
        self.lbl_status.config(text="検索を中止しました", fg="red")
    
    def reset_search(self):
        """検索リセット（キーワードは残す）"""
        try:
            self.selected_cols = []
            self.auto_selected_cols = []
            self.sort_col = None
            self.update_heading_display()
            if self.df is not None:
                self.current_indices = self.df.index.sort_values()
                self.update_list()
            self.lbl_status.config(text=f"全件表示", fg="black")
        except Exception as e:
            messagebox.showerror("Error", f"リセットエラー: {e}")

    def update_list(self):
        """リスト表示更新（最大20000件対応、1文字違い曖昧検索対応）"""
        try:
            # 検索中止フラグをリセット
            self.search_cancelled = False
            
            for item in self.tree.get_children():
                self.tree.delete(item)
            if self.df is None:
                return
            
            # Treeviewのタグ設定（通常検索=通常、一文字違い=アンダーバー＆イタリック）
            self.tree.tag_configure('normal', font=('Meiryo UI', 10))  # 通常検索
            self.tree.tag_configure('fuzzy', font=('Meiryo UI', 10, 'italic underline'))  # 一文字違い検索
            
            disp_cols = self.tree['columns']
            count = 0
            limit = 50000
            
            # 部分一致検索の結果を取得（曖昧マッチを区別するため）
            # 全件表示時は常に通常マッチとして扱う
            if len(self.current_indices) == len(self.df):
                # 全件表示の場合は全て通常表示
                normal_indices = set(self.current_indices)
            else:
                query = self.entry_search.get().strip()
                if query:
                    normal_indices = set(self.df.index[self.get_search_mask(self.df.index)])
                else:
                    normal_indices = set(self.current_indices)
            
            # 全検索結果を表示（通常マッチと曖昧マッチを区別）
            for idx in self.current_indices:
                if count >= limit:
                    break
                
                row = self.df.loc[idx]
                vals = [row[c] for c in disp_cols]
                
                # 曖昧マッチかどうかを判定
                is_fuzzy = idx not in normal_indices
                
                # 背景色情報があれば文字色を設定
                if '__bg_color__' in self.df.columns and pd.notna(row['__bg_color__']) and row['__bg_color__'] != '':
                    bg_color = row['__bg_color__']
                    if is_fuzzy:
                        tag_name = f'fuzzy_bg_{bg_color}'
                        fg_color = self.darken_color(bg_color)
                        self.tree.tag_configure(tag_name, font=('Meiryo UI', 10, 'italic underline'), foreground=fg_color)
                        self.tree.insert('', tk.END, values=vals, iid=f"fuzzy_{idx}", tags=(tag_name,))
                    else:
                        tag_name = f'normal_bg_{bg_color}'
                        fg_color = self.darken_color(bg_color)
                        self.tree.tag_configure(tag_name, font=('Meiryo UI', 10, 'bold'), foreground=fg_color)
                        self.tree.insert('', tk.END, values=vals, iid=str(idx), tags=(tag_name,))
                else:
                    if is_fuzzy:
                        self.tree.insert('', tk.END, values=vals, iid=f"fuzzy_{idx}", tags=('fuzzy',))
                    else:
                        self.tree.insert('', tk.END, values=vals, iid=str(idx), tags=('normal',))
                count += 1
            
            # 表示制限の警告を改善（重複防止）
            if len(self.current_indices) > limit:
                current_text = self.lbl_status.cget('text')
                if "(表示制限:" not in current_text:
                    self.lbl_status.config(text=f"{current_text} (表示制限:先頭{limit}件)", fg="red")
        except Exception as e:
            logging.error(f"リスト更新エラー: {e}")
            messagebox.showerror("Error", f"リスト更新エラー: {e}")

    def on_item_double_click(self, event):
        """ダブルクリック：関係図生成"""
        try:
            # データが読み込まれているか確認
            if self.df is None or len(self.df) == 0:
                messagebox.showwarning("警告", "データが読み込まれていません。")
                return
            
            region = self.tree.identify("region", event.x, event.y)
            if region != "cell":
                return
            
            item_id = self.tree.focus()
            if not item_id:
                return
            
            # 曖昧マッチの場合は"fuzzy_123"形式なので、数値部分を抽出
            if item_id.startswith('fuzzy_'):
                idx = int(item_id[6:])  # "fuzzy_"を除去
            else:
                idx = int(item_id)
            
            # インデックスが有効か確認
            if idx not in self.df.index:
                messagebox.showwarning("警告", "選択された行が見つかりません。")
                return
            
            # '登録名'列が存在するか確認
            if '登録名' not in self.df.columns:
                messagebox.showerror("エラー", "'登録名'列が見つかりません。")
                return
            
            name = self.df.loc[idx, '登録名']
            if name and str(name).strip() != '':
                self.generate_graph(str(name))
            else:
                messagebox.showwarning("警告", "登録名が空です。")
        except Exception as e:
            err_detail = traceback.format_exc()
            messagebox.showerror("Error", f"ダブルクリック処理エラー:\n{e}\n\n詳細:\n{err_detail}")

    def generate_graph(self, center_person):
        """関係図生成"""
        try:
            self.config(cursor="wait")
            depth = self.graph_depth.get()
            generate_customer_graph(self.df, center_person, max_depth=depth)
        except ValueError as e:
            messagebox.showwarning("Info", str(e))
        except Exception as e:
            err_detail = traceback.format_exc()
            self.load_failed(f"グラフ生成エラー: {str(e)}", err_detail)
        finally:
            self.config(cursor="")
    
    def darken_color(self, hex_color):
        """16進数カラーコードを暗くする（文字色用）"""
        try:
            # '#'を除去
            hex_color = hex_color.lstrip('#')
            
            # RGB値に変換
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
            else:
                return '#000000'  # デフォルトは黒
            
            # 明度を下げる（0.6倍）
            r = int(r * 0.6)
            g = int(g * 0.6)
            b = int(b * 0.6)
            
            # 16進数に戻す
            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return '#000000'  # エラー時は黒
    
    def get_claude_api_key(self):
        """レジストリからClaude API Keyを取得"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, REGISTRY_CLAUDE_API_KEY)
            winreg.CloseKey(key)
            return value
        except:
            return None
    
    def get_claude_model(self):
        """レジストリからClaude Modelを取得"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, REGISTRY_CLAUDE_MODEL)
            winreg.CloseKey(key)
            return value
        except:
            return None
    
    def save_claude_api_key(self, api_key):
        """レジストリにClaude API Keyを保存"""
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
            winreg.SetValueEx(key, REGISTRY_CLAUDE_API_KEY, 0, winreg.REG_SZ, api_key)
            winreg.CloseKey(key)
        except Exception as e:
            logging.error(f"API Key保存エラー: {e}")
    
    def save_claude_model(self, model):
        """レジストリにClaude Modelを保存"""
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
            winreg.SetValueEx(key, REGISTRY_CLAUDE_MODEL, 0, winreg.REG_SZ, model)
            winreg.CloseKey(key)
        except Exception as e:
            logging.error(f"Model保存エラー: {e}")
    
    def auto_fill_furigana(self):
        """フリガナ自動入力機能"""
        try:
            # anthropicライブラリの確認
            if not ANTHROPIC_AVAILABLE:
                messagebox.showerror("エラー", "anthropicライブラリがインストールされていません。\n\npip install anthropic\n\nを実行してください。")
                return
            
            # データが読み込まれているか確認
            if self.df is None:
                messagebox.showwarning("警告", "先にExcelファイルを読み込んでください。")
                return
            
            # 本名列とフリガナ列の確認
            if '本名' not in self.df.columns:
                messagebox.showerror("エラー", "「本名」列が見つかりません。")
                return
            
            if 'フリガナ' not in self.df.columns:
                messagebox.showerror("エラー", "「フリガナ」列が見つかりません。")
                return
            
            # 統合ダイアログを表示
            self.show_furigana_settings_dialog()
                
        except Exception as e:
            messagebox.showerror("エラー", f"フリガナ自動入力エラー: {e}")
            traceback.print_exc()
    
    def validate_claude_api(self, api_key, model, parent_dialog):
        """Claude APIキーとモデルを事前検証"""
        try:
            import anthropic
            
            # 検証中ダイアログを表示
            progress = tk.Toplevel(parent_dialog)
            progress.title("検証中")
            progress.geometry("300x100")
            progress.transient(parent_dialog)
            progress.grab_set()
            
            tk.Label(progress, text="APIキーとモデルを検証中...", 
                    font=("Meiryo UI", 10)).pack(pady=20)
            progress_bar = ttk.Progressbar(progress, mode="indeterminate")
            progress_bar.pack(pady=10)
            progress_bar.start(10)
            
            self.update_idletasks()
            
            # テストAPI呼び出し
            def test_api():
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    message = client.messages.create(
                        model=model,
                        max_tokens=10,
                        messages=[{"role": "user", "content": "test"}]
                    )
                    return True, None
                except Exception as e:
                    return False, str(e)
            
            # 別スレッドで実行
            result = [None, None]
            def run_test():
                result[0], result[1] = test_api()
            
            thread = threading.Thread(target=run_test, daemon=True)
            thread.start()
            thread.join(timeout=10)
            
            progress.destroy()
            
            if result[0] is None:
                messagebox.showerror("タイムアウト", 
                    "API検証がタイムアウトしました。\n\n"
                    "ネットワーク接続を確認してください。")
                return False
            
            if not result[0]:
                error_msg = result[1]
                if "401" in error_msg or "authentication" in error_msg.lower():
                    messagebox.showerror("APIキーエラー",
                        "Claude APIキーが無効です。\n\n"
                        f"エラー: {error_msg}\n\n"
                        "正しいAPIキーを入力してください。\n"
                        "https://console.anthropic.com/settings/keys")
                elif "404" in error_msg or "not_found" in error_msg.lower():
                    messagebox.showerror("モデルエラー",
                        f"指定されたモデル '{model}' が見つかりません。\n\n"
                        f"エラー: {error_msg}\n\n"
                        "利用可能なモデル名を確認してください。\n"
                        "https://console.anthropic.com/")
                elif "insufficient" in error_msg.lower() or "credit" in error_msg.lower():
                    messagebox.showerror("課金エラー",
                        "クレジットが不足しています。\n\n"
                        f"エラー: {error_msg}\n\n"
                        "課金情報を確認してください。\n"
                        "https://console.anthropic.com/settings/billing")
                else:
                    messagebox.showerror("API検証エラー",
                        f"Claude APIの検証に失敗しました。\n\n"
                        f"エラー: {error_msg}")
                return False
            
            return True
            
        except Exception as e:
            messagebox.showerror("エラー", f"API検証エラー: {e}")
            return False
    
    def show_furigana_settings_dialog(self):
        """フリガナ自動入力の統合設定ダイアログ（APIキー、モデル、既存フリガナ処理を1画面で）"""
        dialog = tk.Toplevel(self)
        dialog.title("フリガナ自動入力設定")
        dialog.geometry("600x650")
        dialog.transient(self)
        dialog.grab_set()
        
        # 既存の設定を取得
        saved_api_key = self.get_claude_api_key() or DEFAULT_API_KEY
        saved_model = self.get_claude_model() or DEFAULT_MODEL
        
        # タイトル
        tk.Label(dialog, text="フリガナ自動入力設定", 
                font=("Meiryo UI", 12, "bold")).pack(pady=10)
        
        # APIキー入力
        frame_api = tk.Frame(dialog)
        frame_api.pack(pady=10, padx=20, fill=tk.X)
        tk.Label(frame_api, text="Claude API Key:", font=("Meiryo UI", 10, "bold")).pack(anchor=tk.W)
        entry_api_key = tk.Entry(frame_api, width=70, font=("Meiryo UI", 9))
        entry_api_key.insert(0, saved_api_key)
        entry_api_key.pack(pady=5)
        
        # モデル入力
        frame_model = tk.Frame(dialog)
        frame_model.pack(pady=10, padx=20, fill=tk.X)
        tk.Label(frame_model, text="Claude Model:", font=("Meiryo UI", 10, "bold")).pack(anchor=tk.W)
        entry_model = tk.Entry(frame_model, width=70, font=("Meiryo UI", 9))
        entry_model.insert(0, saved_model)
        entry_model.pack(pady=5)
        
        # リセットボタン
        frame_reset = tk.Frame(dialog)
        frame_reset.pack(pady=5, padx=20, fill=tk.X)
        
        def load_last_used():
            """最終使用設定を読み込み（レジストリから）"""
            registry_api_key = self.get_claude_api_key()
            registry_model = self.get_claude_model()
            
            if registry_api_key:
                entry_api_key.delete(0, tk.END)
                entry_api_key.insert(0, registry_api_key)
            else:
                messagebox.showinfo("情報", "レジストリに保存された設定がありません。")
            
            if registry_model:
                entry_model.delete(0, tk.END)
                entry_model.insert(0, registry_model)
        
        def load_app_default():
            """アプリ搭載設定を読み込み（ソースコードのデフォルト値）"""
            entry_api_key.delete(0, tk.END)
            entry_api_key.insert(0, DEFAULT_API_KEY)
            entry_model.delete(0, tk.END)
            entry_model.insert(0, DEFAULT_MODEL)
            messagebox.showinfo("情報", 
                f"アプリ搭載設定を読み込みました。\n\n"
                f"APIキー: {DEFAULT_API_KEY[:20]}...\n"
                f"モデル: {DEFAULT_MODEL}")
        
        tk.Button(frame_reset, text="最終使用設定", command=load_last_used,
                 bg="#2196F3", fg="white", font=("Meiryo UI", 9),
                 width=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(frame_reset, text="アプリ搭載設定", command=load_app_default,
                 bg="#FF9800", fg="white", font=("Meiryo UI", 9),
                 width=15).pack(side=tk.LEFT, padx=5)
        
        tk.Label(frame_reset, text="← 古い設定が残っている場合は「アプリ搭載設定」を押してください",
                font=("Meiryo UI", 8), fg="red").pack(side=tk.LEFT, padx=5)
        
        # 課金情報リンク
        frame_link = tk.Frame(dialog)
        frame_link.pack(pady=5)
        link_label = tk.Label(frame_link, text="課金情報: https://console.anthropic.com/settings/billing",
                             font=("Meiryo UI", 8), fg="blue", cursor="hand2")
        link_label.pack()
        link_label.bind("<Button-1>", lambda e: os.system(f"start https://console.anthropic.com/settings/billing"))
        
        # 既存フリガナの処理方法
        frame_mode = tk.Frame(dialog)
        frame_mode.pack(pady=10, padx=20, fill=tk.X)
        tk.Label(frame_mode, text="既に()で囲まれたフリガナがある場合:", 
                font=("Meiryo UI", 10, "bold")).pack(anchor=tk.W, pady=5)
        
        mode_var = tk.StringVar(value="skip")
        
        rb1 = tk.Radiobutton(frame_mode, text="スキップ（既存のフリガナをそのまま保持）",
                            variable=mode_var, value="skip", font=("Meiryo UI", 9))
        rb1.pack(anchor=tk.W, pady=2)
        tk.Label(frame_mode, text="  例: ｻﾄｳ(ｻﾄｳﾊﾅｺ) → ｻﾄｳ(ｻﾄｳﾊﾅｺ) (変更なし)",
                font=("Meiryo UI", 8), fg="gray").pack(anchor=tk.W, padx=20)
        
        rb2 = tk.Radiobutton(frame_mode, text="上書き（既存の()を削除して新規生成）",
                            variable=mode_var, value="overwrite", font=("Meiryo UI", 9))
        rb2.pack(anchor=tk.W, pady=2)
        tk.Label(frame_mode, text="  例: ｻﾄｳ(ｻﾄｳﾊﾅｺ) → ｻﾄｳ(ｻﾄｳﾊﾅｺ) (新規生成)",
                font=("Meiryo UI", 8), fg="gray").pack(anchor=tk.W, padx=20)
        
        rb3 = tk.Radiobutton(frame_mode, text="追加（既存のフリガナに新規生成を追加）",
                            variable=mode_var, value="append", font=("Meiryo UI", 9))
        rb3.pack(anchor=tk.W, pady=2)
        tk.Label(frame_mode, text="  例: ｻﾄｳ(ｻﾄｳﾊﾅｺ) → ｻﾄｳ(ｻﾄｳﾊﾅｺ)(ｻﾄｳﾊﾅｺ)",
                font=("Meiryo UI", 8), fg="gray").pack(anchor=tk.W, padx=20)
        
        # ボタン
        frame_buttons = tk.Frame(dialog)
        frame_buttons.pack(pady=20)
        
        def on_ok():
            api_key = entry_api_key.get().strip()
            model = entry_model.get().strip()
            existing_mode = mode_var.get()
            
            if not api_key:
                messagebox.showwarning("警告", "API Keyを入力してください。")
                return
            
            if not model:
                messagebox.showwarning("警告", "Modelを入力してください。")
                return
            
            # APIキーとモデルの事前検証
            dialog.withdraw()  # ダイアログを一時的に隠す
            if not self.validate_claude_api(api_key, model, dialog):
                dialog.deiconify()  # ダイアログを再表示
                return
            
            dialog.destroy()
            self.execute_furigana_generation(api_key, model, existing_mode)
        
        def on_cancel():
            dialog.destroy()
        
        tk.Button(frame_buttons, text="実行", command=on_ok,
                 bg="#4CAF50", fg="white", font=("Meiryo UI", 11, "bold"),
                 width=10).pack(side=tk.LEFT, padx=10)
        
        tk.Button(frame_buttons, text="キャンセル", command=on_cancel,
                 bg="#666", fg="white", font=("Meiryo UI", 11),
                 width=10).pack(side=tk.LEFT, padx=10)
        
        dialog.wait_window()
    
    def execute_furigana_generation(self, api_key, model, existing_mode):
        """フリガナ生成を実行"""
        try:
            from furigana_helper import generate_furigana_batch
            
            # 確認ダイアログ
            total_count = len(self.df)
            result = messagebox.askyesno("確認", 
                f"全{total_count}件の「本名」に対してフリガナを自動入力します。\n\n"
                f"※ Claude APIを使用します（約$0.50-1.00程度）\n"
                f"※ 処理には数分かかる場合があります\n\n"
                f"実行しますか？")
            
            if not result:
                return
            
            # 進捗ダイアログを表示
            progress_dialog = tk.Toplevel(self)
            progress_dialog.title("フリガナ自動入力中...")
            progress_dialog.geometry("450x180")
            progress_dialog.transient(self)
            progress_dialog.grab_set()
            
            tk.Label(progress_dialog, text="フリガナを自動生成中...", 
                    font=("Meiryo UI", 12, "bold")).pack(pady=15)
            
            progress_label = tk.Label(progress_dialog, text="準備中...", font=("Meiryo UI", 10))
            progress_label.pack(pady=5)
            
            status_label = tk.Label(progress_dialog, text="", font=("Meiryo UI", 9), fg="gray")
            status_label.pack(pady=5)
            
            progress_bar = ttk.Progressbar(progress_dialog, orient="horizontal", 
                                          length=400, mode="determinate")
            progress_bar.pack(pady=15)
            progress_bar["maximum"] = 100
            
            self.update_idletasks()
            
            # バックグラウンドで処理
            def process():
                try:
                    import openpyxl
                    
                    def update_progress(current, total, batch_num, total_batches, status):
                        """進捗を更新"""
                        progress = int((current / total) * 100)
                        self.after(0, lambda: progress_bar.configure(value=progress))
                        self.after(0, lambda: progress_label.configure(
                            text=f"処理中: {current}/{total}件 (バッチ {batch_num}/{total_batches})"))
                        self.after(0, lambda: status_label.configure(text=status))
                    
                    # データ準備
                    self.after(0, lambda: progress_label.configure(text="データ準備中..."))
                    names = self.df['本名'].tolist()
                    existing_furigana = self.df['フリガナ'].tolist()
                    
                    # Claude APIでフリガナ生成
                    self.after(0, lambda: status_label.configure(text="Claude APIでフリガナを生成中..."))
                    results = generate_furigana_batch(
                        names, existing_furigana, api_key, model, 
                        existing_mode=existing_mode, 
                        progress_callback=update_progress
                    )
                    
                    # 成功したらAPIキーとモデルをレジストリに保存
                    self.save_claude_api_key(api_key)
                    self.save_claude_model(model)
                    
                    # openpyxlで既存ファイルを直接更新
                    if self.last_loaded_path:
                        self.after(0, lambda: progress_label.configure(text="Excelファイルを更新中..."))
                        self.after(0, lambda: status_label.configure(text="ファイルを読み込んでいます..."))
                        
                        wb = openpyxl.load_workbook(self.last_loaded_path, data_only=True)
                        ws = wb.active
                        
                        # ヘッダー行を確認
                        headers = [cell.value for cell in ws[1]]
                        name_col = headers.index('本名') + 1
                        furigana_col = headers.index('フリガナ') + 1
                        
                        # フリガナを更新
                        self.after(0, lambda: status_label.configure(text="フリガナを書き込んでいます..."))
                        updated_count = 0
                        total_rows = ws.max_row - 1
                        for row_idx in range(2, ws.max_row + 1):
                            name = ws.cell(row=row_idx, column=name_col).value
                            if pd.notna(name) and name != '' and name in results:
                                ws.cell(row=row_idx, column=furigana_col).value = results[name]
                                updated_count += 1
                            
                            # 進捗更新（10行ごと）
                            if row_idx % 10 == 0:
                                progress = int(((row_idx - 1) / total_rows) * 100)
                                self.after(0, lambda p=progress: progress_bar.configure(value=progress))
                                self.after(0, lambda r=row_idx-1, t=total_rows: progress_label.configure(
                                    text=f"書き込み中: {r}/{t}行"))
                        
                        # ファイルを保存
                        self.after(0, lambda: progress_label.configure(text="ファイルを保存中..."))
                        self.after(0, lambda: status_label.configure(text="保存しています..."))
                        wb.save(self.last_loaded_path)
                        wb.close()
                        
                        # 保存後にファイルを再読み込み
                        self.after(0, lambda: progress_label.configure(text="ファイルを再読み込み中..."))
                        self.after(0, lambda: status_label.configure(text="最新のデータを読み込んでいます..."))
                        
                        # ファイルを再読み込みして表示を更新
                        self.after(0, lambda: progress_dialog.destroy())
                        self.after(0, lambda: messagebox.showinfo("完了", 
                            f"フリガナの自動入力が完了しました。\n\n"
                            f"処理件数: {updated_count}件\n"
                            f"ファイルに保存しました。"))
                        self.after(0, lambda: self.process_load(self.last_loaded_path))
                    else:
                        self.after(0, lambda: progress_dialog.destroy())
                        self.after(0, lambda: messagebox.showwarning("警告", 
                            "ファイルパスが不明なため保存できませんでした。"))
                    
                except Exception as e:
                    self.after(0, lambda: progress_dialog.destroy())
                    error_msg = str(e)
                    
                    # APIキーエラーまたは404エラー、課金エラーの場合は通知
                    if "401" in error_msg or "authentication" in error_msg.lower() or "api key" in error_msg.lower():
                        messagebox.showerror("APIキーエラー",
                            f"Claude APIキーが無効です。\n\n"
                            f"エラー: {error_msg}\n\n"
                            f"正しいAPIキーを入力してください。")
                    elif "404" in error_msg or "not_found" in error_msg.lower():
                        messagebox.showerror("モデルエラー",
                            f"指定されたモデルが見つかりません。\n\n"
                            f"エラー: {error_msg}\n\n"
                            f"利用可能なモデル名を確認してください。\n"
                            f"https://console.anthropic.com/")
                    elif "insufficient" in error_msg.lower() or "credit" in error_msg.lower() or "quota" in error_msg.lower():
                        messagebox.showerror("課金エラー",
                            f"クレジットが不足しています。\n\n"
                            f"エラー: {error_msg}\n\n"
                            f"課金情報を確認してください。\n"
                            f"https://console.anthropic.com/settings/billing")
                    else:
                        messagebox.showerror("エラー", f"フリガナ生成エラー: {e}")
                        traceback.print_exc()
            
            # スレッドで実行
            threading.Thread(target=process, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("エラー", f"フリガナ生成実行エラー: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    app = CustomerApp()
    app.mainloop()
