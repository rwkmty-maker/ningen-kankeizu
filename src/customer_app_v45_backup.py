# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import pandas as pd
import threading
import datetime
import traceback
import time
import os
import logging

from utils import (
    hira_to_kata, normalize_text_unified, get_natural_sort_key, clean_referrer,
    parse_fuzzy_date, parse_excel_date, format_date_text, generate_era_candidates
)
from graph import generate_customer_graph

logging.basicConfig(level=logging.CRITICAL)


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
            if path.endswith('.xlsx'):
                self.process_load(path)
        except Exception as e:
            messagebox.showerror("Error", f"ドロップ処理エラー: {e}")

    def start_load_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx")])
        if path:
            self.process_load(path)

    def reload_excel(self):
        if self.last_loaded_path and os.path.exists(self.last_loaded_path):
            self.process_load(self.last_loaded_path)
        else:
            messagebox.showerror("エラー", "再読み込みするファイルが見つかりません。")

    def process_load(self, file_path):
        if hasattr(self, 'loading') and self.loading:
            return
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
                if col not in df.columns:
                    raise Exception(f"必須列「{col}」不足")

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
                df['__birth_search_index__'] = birth_col_dates.apply(self._generate_birth_search_index)

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

    def _generate_birth_search_index(self, dt):
        """生年月日から検索用インデックスを生成（元号省略形を含む）"""
        if pd.isna(dt):
            return ""
        if not isinstance(dt, (datetime.datetime, pd.Timestamp, datetime.date)):
            return ""
        try:
            candidates = generate_era_candidates(dt.year, dt.month, dt.day)
            return " ".join(candidates)
        except:
            return ""

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
        
        disp_cols = [c for c in df.columns if not c.startswith('__') and c != 'search_index']
        self.tree['columns'] = disp_cols
        for c in disp_cols:
            self.tree.heading(c, text=c)
            width = 100
            
            if c == '会員ID':
                width = 50
            elif c in ['登録名', 'フリガナ', '旧登録名', '本名']:
                width = 120
            elif c == '生年月日':
                width = 170
            elif '電話番号' in c:
                width = 150
            elif c == '住所':
                width = 340
            elif c == '備考':
                width = 300
            elif c in ['紹介者', 'グループ']:
                width = 100
            elif c in ['記入者', 'アナウンス可能(時間帯)', 'チケット欄', '身分証1', '身分証2', '身分証チェック']:
                width = 50
            
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

    def update_heading_display(self):
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

    def set_cols_and_search(self, cols, sort_by_birth=False):
        if self.df is None:
            return
        valid_cols = [c for c in cols if c in self.df.columns]
        self.selected_cols = valid_cols
        self.update_heading_display()
        if sort_by_birth:
            self.sort_col = '生年月日'
            self.sort_asc = True
            self.run_search_new(apply_sort=True)
        else:
            self.run_search_new(apply_sort=False)

    def get_search_mask(self, source_indices):
        if self.df is None:
            return None
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
        if self.selected_cols and '生年月日' not in self.selected_cols:
            do_date_search = False
        
        if do_date_search and '__sort_birth__' in self.df.columns:
            if target_dates:
                def check_date_match(dt):
                    if pd.isna(dt):
                        return False
                    if not isinstance(dt, (datetime.datetime, pd.Timestamp, datetime.date)):
                        return False
                    for (y, m, d) in target_dates:
                        match = True
                        if y is not None and dt.year != y:
                            match = False
                        if m is not None and dt.month != m:
                            match = False
                        if d is not None and dt.day != d:
                            match = False
                        if match:
                            return True
                    return False
                date_mask = subset['__sort_birth__'].apply(check_date_match)
                mask = mask | date_mask
            
            if '__birth_search_index__' in self.df.columns and q_norm_base:
                nums_only = ''.join([c for c in query if c.isdigit()])
                if nums_only:
                    birth_index_mask = subset['__birth_search_index__'].str.contains(nums_only, na=False, regex=False)
                    mask = mask | birth_index_mask

        if not query.strip():
            mask = pd.Series([True] * len(subset), index=subset.index)
        return mask

    def run_search_new(self, apply_sort=False):
        if self.df is None:
            return
        mask = self.get_search_mask(self.df.index)
        self.current_indices = self.df.index[mask]
        
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

    def run_search_filter(self):
        if self.df is None:
            return
        mask = self.get_search_mask(self.current_indices)
        self.current_indices = self.current_indices[mask]
        if self.sort_col:
            self.run_single_sort()
        else:
            self.update_list()
        self.update_status_msg("絞り込み結果")

    def run_single_sort(self):
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

        try:
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
        msg = f"{prefix}: {len(self.current_indices)}件"
        if self.selected_cols:
            msg += f" (対象: {','.join(self.selected_cols)})"
        self.lbl_status.config(text=msg, fg="orange")

    def copy_selection(self, event):
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
        for item in self.tree.get_children():
            self.tree.delete(item)
        if self.df is None:
            return
        disp_cols = self.tree['columns']
        count = 0
        limit = 5000 
        for idx in self.current_indices:
            if count >= limit:
                break
            row = self.df.loc[idx]
            vals = [row[c] for c in disp_cols]
            self.tree.insert('', tk.END, values=vals, iid=str(idx))
            count += 1
        if len(self.current_indices) > limit:
            self.lbl_status.config(text=f"{self.lbl_status.cget('text')} (表示制限:先頭{limit}件)", fg="red")

    def on_item_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        item_id = self.tree.focus()
        if not item_id:
            return
        idx = int(item_id)
        name = self.df.loc[idx, '登録名']
        if name:
            self.generate_graph(name)

    def generate_graph(self, center_person):
        try:
            self.config(cursor="wait")
            generate_customer_graph(self.df, center_person)
        except ValueError as e:
            messagebox.showwarning("Info", str(e))
        except Exception as e:
            err_detail = traceback.format_exc()
            self.load_failed(f"グラフ生成エラー: {str(e)}", err_detail)
        finally:
            self.config(cursor="")


if __name__ == "__main__":
    app = CustomerApp()
    app.mainloop()
